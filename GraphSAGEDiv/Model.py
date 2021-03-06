from GraphSAGEDiv.NeighSampler import UniformNeighborSampler
from GraphSAGEDiv.Layer import *
from Util import *
from GraphSAGEDiv import DPP

class InducieveLearningQA(nn.Module):
    def __init__(self, args,
                 user_count,
                 content_count,
                 adj,
                 adj_edge,
                 content_embed,
                 user_context_embed,
                 word2vec
                 ):
        super(InducieveLearningQA, self).__init__()
        self.args = args
        self.adj = adj
        self.adj_edge = adj_edge
        self.user_count = user_count
        self.hidden_state_size = (2 if self.args.bidirectional else 1) * self.args.lstm_hidden_size


        ##############
        #  network structure init
        ##############
        self.user_embed = nn.Embedding(user_count, self.hidden_state_size)
        self.content_embed = content_embed
        self.word2vec_embed = nn.Embedding.from_pretrained(word2vec)


        self.sampler = UniformNeighborSampler(self.adj, self.adj_edge)
        self.q_aggregate = AttentionAggregate(self.hidden_state_size, self.hidden_state_size, self.hidden_state_size)
        self.u_aggregate = AttentionAggregate(self.hidden_state_size, self.hidden_state_size, self.hidden_state_size)
        self.q_node_generate = NodeGenerate(self.hidden_state_size)
        self.u_node_generate = NodeGenerate(self.hidden_state_size)
        self.a_edge_generate = EdgeGenerate()

        self.w_q = nn.Linear(self.hidden_state_size, self.hidden_state_size)
        self.w_a = nn.Linear(self.hidden_state_size, self.hidden_state_size)
        self.w_u = nn.Linear(self.hidden_state_size, self.hidden_state_size)


        if self.args.is_classification:
            self.w_final = nn.Linear(self.hidden_state_size, args.num_class)
        else:
            self.w_final = nn.Linear(self.hidden_state_size, 1)
        self.cnn_lr = nn.Conv2d(1, self.hidden_state_size, (3, args.embed_size))
        self.bn = nn.BatchNorm1d(self.args.lstm_hidden_size)
        self.dropout = nn.Dropout(args.drop_out_lstm)

    def content_cnn(self, content):
        shape = content.shape
        content = content.view(-1, 1, shape[-2], shape[-1])
        content_cnn, _ = torch.max(torch.relu(self.cnn_lr(content)), dim=-2)
        content_cnn = self.bn(content_cnn)
        content_cnn = self.dropout(content_cnn)
        shape1 = []
        for i in range(len(shape) - 2):
            shape1.append(shape[i])
        shape1.append(self.hidden_state_size)
        content_cnn = content_cnn.view(shape1)
        return content_cnn



    def neighbor_sample(self, item, depth, neighbor_count_list):
        neighbor_node = []
        neighbor_edge = []
        neighbor_node.append(item)

        for i in range(depth):
            neighbor_node_layer, neighbor_edge_layer = self.sampler.sample(neighbor_node[i], neighbor_count_list[i])
            neighbor_node.append(neighbor_node_layer)
            neighbor_edge.append(neighbor_edge_layer)

        return neighbor_node, neighbor_edge




    def forward(self, question, answer_edge, user, need_feature=False):
        #sample neighbors
        # q <- a -> u <- a -> u
        # u <- a -> q <- a -> q
        question_neighbors, question_neighbors_edge = self.neighbor_sample(question, self.args.graphsage_depth, self.args.neighbor_number_list)
        user_neighbors, user_neigbor_edge = self.neighbor_sample(user, self.args.graphsage_depth, self.args.neighbor_number_list)

        depth = len(question_neighbors)
        #load embedding
        for i in range(depth):
            if i % 2 == 0:
                question_embed = self.content_embed.content_embed(question_neighbors[i] - self.user_count)
                question_embed_word2vec = self.word2vec_embed(question_embed)
                question_lstm_embed = self.content_cnn(question_embed_word2vec)
                question_neighbors[i] = question_lstm_embed


                user_neighbors[i] = self.user_embed(user_neighbors[i])
            else:
                question_neighbors[i] = self.user_embed(question_neighbors[i])

                question_embed = self.content_embed.content_embed(user_neighbors[i] - self.user_count)
                question_embed_word2vec = self.word2vec_embed(question_embed)
                question_lstm_embed = self.content_cnn(question_embed_word2vec)

                user_neighbors[i] = question_lstm_embed

        for i in range(depth-1):
            question_edge_embed = self.content_embed.content_embed(question_neighbors_edge[i] - self.user_count)
            question_edge_word2vec = self.word2vec_embed(question_edge_embed)
            question_edge_lstm = self.content_cnn(question_edge_word2vec)
            question_neighbors_edge[i] = question_edge_lstm

            user_edge_embed = self.content_embed.content_embed(user_neigbor_edge[i] - self.user_count)
            user_edge_word2vec = self.word2vec_embed(user_edge_embed)
            user_edge_lstm = self.content_cnn(user_edge_word2vec)
            user_neigbor_edge[i] = user_edge_lstm

        answer_embed_layer = self.content_embed.content_embed(answer_edge - self.user_count)
        answer_embed_word2vec = self.word2vec_embed(answer_embed_layer)
        answer_lstm_embed = self.content_cnn(answer_embed_word2vec)
        answer_edge_feaure = answer_lstm_embed




        #aggregate
        for i in range(depth - 1):
            layer_no = depth - i - 1
            if layer_no % 2 == 0:
                question_layer = question_neighbors[layer_no]
                question_edge = question_neighbors_edge[layer_no - 1]
                question_edge = self.a_edge_generate(question_edge, question_layer, question_neighbors[layer_no - 1])
                question_neighbor_feature = self.u_aggregate(question_layer, question_edge, question_neighbors[layer_no - 1])
                question_neighbors[layer_no - 1] = self.u_node_generate(question_neighbors[layer_no - 1], question_neighbor_feature)

                user_layer = user_neighbors[layer_no]
                user_edge = user_neigbor_edge[layer_no - 1]
                # update the edge based on two sides of nodes
                user_edge = self.a_edge_generate(user_edge, user_layer, user_neighbors[layer_no - 1])
                user_neigbor_feature = self.q_aggregate(user_layer, user_edge, user_neighbors[layer_no - 1])
                user_neighbors[layer_no - 1] = self.q_node_generate(user_neighbors[layer_no - 1], user_neigbor_feature)

            else:
                user_layer = question_neighbors[layer_no]
                user_edge = question_neighbors_edge[layer_no - 1]
                user_edge = self.a_edge_generate(user_edge, user_layer, question_neighbors[layer_no - 1])
                user_neighbor_feature = self.q_aggregate(user_layer, user_edge, question_neighbors[layer_no-1])
                question_neighbors[layer_no - 1] = self.q_node_generate(question_neighbors[layer_no - 1],
                                                                    user_neighbor_feature)

                question_layer = user_neighbors[layer_no]
                question_edge = user_neigbor_edge[layer_no - 1]
                question_edge= self.a_edge_generate(question_edge, question_layer, user_neighbors[layer_no - 1])
                question_neigbor_feature = self.q_aggregate(question_layer, question_edge, user_neighbors[layer_no-1])

                user_neighbors[layer_no - 1] = self.q_node_generate(user_neighbors[layer_no - 1], question_neigbor_feature)

        #score edge strength
        score = torch.tanh(self.w_a(answer_edge_feaure) + self.w_q(question_neighbors[0]) + self.w_u(user_neighbors[0]))
        if self.args.is_classification:
            score = F.log_softmax(self.w_final(score), dim=-1)
            predic = torch.argmax(score, dim=-1)
            return_list = [score, predic]
        else:
            score = self.w_final(score).view(-1,)
            return_list = [score]
        # if need_feature:
        #     answer_vec = answer_edge_feaure.detach()
        #     return_list.append(answer_vec)
        return tuple(return_list)