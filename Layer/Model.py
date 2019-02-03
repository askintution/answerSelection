from Layer.NeighSampler import UniformNeighborSampler
from Layer.Layer import *
from Util import *

class InducieveLearning(nn.Module):
    def __init__(self, args,
                 user_count,
                 adj,
                 adj_edge,
                 content,
                 word2vec
                 ):
        super(InducieveLearning, self).__init__()
        self.args = args
        self.adj = adj
        self.adj_edge = adj_edge
        self.user_count = user_count

        ##############
        #  network structure init
        ##############
        self.user_embed = nn.Embedding(user_count, args.user_embed_dim)
        self.content = content
        self.word2vec_embed = nn.Embedding.from_pretrained(word2vec)

        self.lstm = LSTM(args)

        self.sampler = UniformNeighborSampler(self.adj, self.adj_edge)
        self.q_aggregate = Aggregate(args.lstm_hidden_size, args.lstm_hidden_size, args.lstm_hidden_size)
        self.u_aggregate = Aggregate(args.lstm_hidden_size, args.lstm_hidden_size, args.lstm_hidden_size)
        self.q_node_generate = NodeGenerate(args.lstm_hidden_size)
        self.u_node_generate = NodeGenerate(args.lstm_hidden_size)
        self.a_edge_generate = EdgeGenerate()

        self.w_q = nn.Linear(args.lstm_hidden_size, args.lstm_hidden_size)
        self.w_a = nn.Linear(args.lstm_hidden_size, args.lstm_hidden_size)
        self.w_u = nn.Linear(args.lstm_hidden_size, args.lstm_hidden_size)
        self.w_final = nn.Linear(args.lstm_hidden_size, args.num_class)



    def content_embed(self,batch_id):
        shape = [*batch_id.shape]
        shape.append(len(self.content[0]))
        shape = tuple(shape)
        batch_id = batch_id.view(-1, )
        content = self.content[batch_id]
        content = content.view(shape)
        return content



    def neighbor_sample(self, item, depth, neighbor_count_list):
        neighbor_node = []
        neighbor_edge = []
        neighbor_node.append(item)

        for i in range(depth):
            neighbor_node_layer, neighbor_edge_layer = self.sampler.sample(neighbor_node[i], neighbor_count_list[i])
            neighbor_node.append(neighbor_node_layer)
            neighbor_edge.append(neighbor_edge_layer)

        return neighbor_node, neighbor_edge




    def forward(self, question, answer_edge, user):
        #sample neighbors
        # q <- a -> u <- a -> u
        # u <- a -> q <- a -> q
        question_neighbors, question_neighbors_edge = self.neighbor_sample(question, self.args.depth, self.args.neighbor_number_list)
        user_neighbors, user_neigbor_edge = self.neighbor_sample(user, self.args.depth, self.args.neighbor_number_list)

        depth = len(question_neighbors)
        #load embedding
        for i in range(depth):
            if i % 2 == 0:
                question_embed = self.content_embed(question_neighbors[i] - self.user_count)
                question_embed_word2vec = self.word2vec_embed(question_embed)
                question_lstm_embed = self.lstm(question_embed_word2vec)
                question_neighbors[i] = question_lstm_embed


                user_neighbors[i] = self.user_embed(user_neighbors[i])
            else:
                question_neighbors[i] = self.user_embed(question_neighbors[i])

                question_embed = self.content_embed(user_neighbors[i] - self.user_count)
                question_embed_word2vec = self.word2vec_embed(question_embed)
                question_lstm_embed = self.lstm(question_embed_word2vec)
                user_neighbors[i] = question_lstm_embed

        for i in range(depth-1):
            question_edge_embed = self.content_embed(question_neighbors_edge[i] - self.user_count)
            question_edge_word2vec = self.word2vec_embed(question_edge_embed)
            question_edge_lstm = self.lstm(question_edge_word2vec)
            question_neighbors_edge[i] = question_edge_lstm

            user_edge_embed = self.content_embed(user_neigbor_edge[i] - self.user_count)
            user_edge_word2vec = self.word2vec_embed(user_edge_embed)
            user_edge_lstm = self.lstm(user_edge_word2vec)
            user_neigbor_edge[i] = user_edge_lstm

        answer_embed_layer = self.content_embed(answer_edge - self.user_count)
        answer_embed_word2vec = self.word2vec_embed(answer_embed_layer)
        answer_lstm_embed = self.lstm(answer_embed_word2vec)
        answer_edge = answer_lstm_embed




        #aggregate
        for i in range(depth - 1):
            layer_no = depth - i - 1
            if layer_no % 2 == 0:
                question_layer = question_neighbors[layer_no]
                question_edge = question_neighbors_edge[layer_no - 1]
                question_edge = self.a_edge_generate(question_edge, question_layer, question_neighbors[layer_no - 1])
                question_neighbor_feature = self.u_aggregate(question_layer, question_edge)
                question_neighbors[layer_no - 1] = self.u_node_generate(question_neighbors[layer_no - 1], question_neighbor_feature)

                user_layer = user_neighbors[layer_no]
                user_edge = user_neigbor_edge[layer_no - 1]
                # update the edge based on two sides of nodes
                user_edge = self.a_edge_generate(user_edge, user_layer, user_neighbors[layer_no - 1])
                user_neigbor_feature = self.q_aggregate(user_layer, user_edge)
                user_neighbors[layer_no - 1] = self.q_node_generate(user_neighbors[layer_no - 1], user_neigbor_feature)

            else:
                user_layer = question_neighbors[layer_no]
                user_edge = question_neighbors_edge[layer_no - 1]
                user_edge = self.a_edge_generate(user_edge, user_layer, question_neighbors[layer_no - 1])
                user_neighbor_feature = self.q_aggregate(user_layer, user_edge)
                question_neighbors[layer_no - 1] = self.q_node_generate(question_neighbors[layer_no - 1],
                                                                    user_neighbor_feature)

                question_layer = user_neighbors[layer_no]
                question_edge = user_neigbor_edge[layer_no - 1]
                question_edge= self.a_edge_generate(question_edge, question_layer, user_neighbors[layer_no - 1])
                question_neigbor_feature = self.q_aggregate(question_layer, question_edge)

                user_neighbors[layer_no - 1] = self.q_node_generate(user_neighbors[layer_no - 1], question_neigbor_feature)

        #score edge strength
        score = F.tanh(self.w_a(answer_edge) + self.w_q(question_neighbors[0]) + self.w_u(user_neighbors[0]))
        score = F.log_softmax(self.w_final(score),dim=-1)
        predic = torch.argmax(score,dim=-1)

        return score, predic

