from GraphSAGEDiv.NeighSampler import UniformNeighborSampler
from GraphSAGEDiv.LayerKey import *
from Util import *

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
        self.value_dim = args.value_dim
        self.key_dim = (2 if self.args.bidirectional else 1) * self.args.lstm_hidden_size


        ##############
        #  network structure init
        ##############
        # self.user_embed = user_embed
        self.user_context_embed = user_context_embed
        self.content_embed = content_embed
        self.word2vec_embed = nn.Embedding.from_pretrained(word2vec)
        self.content_value_embed = nn.Embedding(content_count, self.value_dim)
        self.user_value_embed = nn.Embedding(user_count, self.value_dim)
        self.lstm = LSTM_MeanPool(args)

        self.sampler = UniformNeighborSampler(self.adj, self.adj_edge)
        # self.q_aggregate = AttentionAggregate_Weight(self.key_dim)
        self.q_aggregate = AttentionAggregate_Cos()
        # self.u_aggregate = AttentionAggregate_Weight(self.key_dim)
        self.u_aggregate = AttentionAggregate_Cos()
        self.Keymiddle = MiddleGeneration(self.key_dim)
        self.Valuemiddle = MiddleGeneration(self.value_dim)

        #Aggregate(self.hidden_state_size, self.hidden_state_size, self.hidden_state_size)
        #AttentionAggregate_Weight(self.hidden_state_size)
        # Aggregate(self.hidden_state_size, self.hidden_state_size, self.hidden_state_size)
        self.q_node_generate = NodeGenerate_GRU_Forget_Gate(self.value_dim, self.value_dim)
        self.u_node_generate = NodeGenerate_GRU_Forget_Gate(self.value_dim, self.value_dim)
        self.a_edge_generate = EdgeGenerate()

        self.num_class = 2 if self.args.is_classification else 1
        self.score_fn = ARMNLScore(self.value_dim + self.key_dim)
        # self.score_fn = WeightScore(self.value_dim, self.num_class)


        #ATTENTION: use CNN to generate init vector question and answer
        self.cnn_lr = nn.Conv2d(1, self.key_dim, (3, args.embed_size))
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
        shape1.append(self.key_dim)
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
        question_neighbors_value_list = []
        user_neighbors_value_list = []
        question_neighbors_edge_value_list = []
        user_neighbors_edge_value_list = []

        depth = len(question_neighbors)
        #load embedding
        for i in range(depth):
            if i % 2 == 0:
                #ATTENTION: key and value have the same init value
                question_neighbors_value_list.append(self.content_value_embed(question_neighbors[i] - self.user_count))
                # question_neighbors_value_list.append(self.content_cnn(self.word2vec_embed(self.content_embed.content_embed(question_neighbors[i] - self.user_count))))

                question_embed = self.content_embed.content_embed(question_neighbors[i] - self.user_count)
                question_embed_word2vec = self.word2vec_embed(question_embed)
                question_lstm_embed = self.content_cnn(question_embed_word2vec)
                question_neighbors[i] = question_lstm_embed

                #ATTENTION: user context embedding
                user_neighbors_value_list.append(self.user_value_embed(user_neighbors[i]))
                # user_neighbors_value_list.append(self.content_cnn(self.word2vec_embed(self.user_context_embed.content_embed(user_neighbors[i]))))

                user_embed = self.word2vec_embed(self.user_context_embed.content_embed(user_neighbors[i]))
                user_embed = self.content_cnn(user_embed)
                user_neighbors[i] = user_embed

            else:
                question_neighbors_value_list.append(self.user_value_embed(question_neighbors[i]))
                # question_neighbors_value_list.append(self.content_cnn(self.word2vec_embed(self.user_context_embed.content_embed(question_neighbors[i]))))

                user_embed = self.word2vec_embed(self.user_context_embed.content_embed(question_neighbors[i]))
                user_embed = self.content_cnn(user_embed)
                question_neighbors[i] = user_embed


                user_neighbors_value_list.append(self.content_value_embed(user_neighbors[i] - self.user_count))
                # user_neighbors_value_list.append(self.content_cnn(self.word2vec_embed(self.content_embed.content_embed(user_neighbors[i] - self.user_count))))

                question_embed = self.content_embed.content_embed(user_neighbors[i] - self.user_count)
                question_embed_word2vec = self.word2vec_embed(question_embed)
                question_lstm_embed = self.content_cnn(question_embed_word2vec)
                user_neighbors[i] = question_lstm_embed

        for i in range(depth-1):
            question_neighbors_edge_value_list.append(self.content_value_embed(question_neighbors_edge[i] - self.user_count))
            # question_neighbors_edge_value_list.append(self.content_cnn(self.word2vec_embed(self.content_embed.content_embed()))self.content_value_embed())

            question_edge_embed = self.content_embed.content_embed(question_neighbors_edge[i] - self.user_count)
            question_edge_word2vec = self.word2vec_embed(question_edge_embed)
            question_edge_lstm = self.content_cnn(question_edge_word2vec)
            question_neighbors_edge[i] = question_edge_lstm


            user_neighbors_edge_value_list.append(
                self.content_value_embed(user_neigbor_edge[i] - self.user_count)
            )
            user_edge_embed = self.content_embed.content_embed(user_neigbor_edge[i] - self.user_count)
            user_edge_word2vec = self.word2vec_embed(user_edge_embed)
            user_edge_lstm = self.content_cnn(user_edge_word2vec)
            user_neigbor_edge[i] = user_edge_lstm

        answer_embed_layer = self.content_embed.content_embed(answer_edge - self.user_count)
        answer_embed_word2vec = self.word2vec_embed(answer_embed_layer)
        answer_lstm_embed = self.content_cnn(answer_embed_word2vec)

        answer_value = self.content_value_embed(answer_edge - self.user_count)


        #aggregate
        for i in range(depth - 1):
            layer_no = depth - i - 1
            if layer_no % 2 == 0:
                question_layer = question_neighbors[layer_no]
                question_layer_value = question_neighbors_value_list[layer_no]
                question_edge = question_neighbors_edge[layer_no - 1]
                question_edge_value = question_neighbors_edge_value_list[layer_no - 1]
                question_edge_value = self.a_edge_generate(
                    question_layer, question_neighbors[layer_no - 1], question_edge,
                    question_layer_value, question_neighbors_value_list[layer_no - 1], question_edge_value
                )

                question_neighbor_value = self.u_aggregate(
                    self.Keymiddle(question_layer, question_edge),  question_neighbors[layer_no - 1],
                    self.Valuemiddle(question_layer_value, question_edge_value))

                question_neighbors_value_list[layer_no - 1] = \
                    self.u_node_generate(question_neighbors_value_list[layer_no - 1], question_neighbor_value)


                user_layer = user_neighbors[layer_no]
                user_layer_value = user_neighbors_value_list[layer_no]
                user_edge = user_neigbor_edge[layer_no - 1]
                user_edge_value = user_neighbors_edge_value_list[layer_no - 1]
                # update the edge based on two sides of nodes
                user_edge_value = self.a_edge_generate(user_layer, user_neighbors[layer_no - 1], user_edge,
                                                       user_layer_value, user_neighbors_value_list[layer_no - 1], user_edge_value
                                                       )

                user_neighbor_value = self.q_aggregate(self.Keymiddle(user_layer, user_edge), user_neighbors[layer_no - 1],
                                                       self.Valuemiddle(user_layer_value, user_edge_value))
                user_neighbors_value_list[layer_no - 1] = self.q_node_generate(user_neighbors_value_list[layer_no - 1], user_neighbor_value)

            else:
                #get key
                user_layer = question_neighbors[layer_no]
                #get value
                user_layer_value = question_neighbors_value_list[layer_no]
                user_edge = question_neighbors_edge[layer_no - 1]
                user_edge_value = question_neighbors_edge_value_list[layer_no - 1]
                user_edge_value = self.a_edge_generate(
                    user_layer, question_neighbors[layer_no - 1], user_edge,
                    user_layer_value, question_neighbors_value_list[layer_no - 1], user_edge_value
                )

                user_neighbor_value = self.q_aggregate(
                    self.Keymiddle(user_layer, user_edge), question_neighbors[layer_no - 1],
                    self.Valuemiddle(user_layer_value, user_edge_value)
                )
                question_neighbors_value_list[layer_no - 1] = self.q_node_generate(question_neighbors_value_list[layer_no - 1], user_neighbor_value)


                question_layer = user_neighbors[layer_no]
                question_layer_value = user_neighbors_value_list[layer_no]
                question_edge = user_neigbor_edge[layer_no - 1]
                question_edge_value = user_neighbors_edge_value_list[layer_no - 1]

                question_edge_value = \
                    self.a_edge_generate(
                        question_layer, user_neighbors[layer_no - 1], question_edge,
                        question_layer_value, user_neighbors_value_list[layer_no - 1], question_edge_value
                    )


                question_neighbor_feature = self.u_aggregate(
                    self.Keymiddle(question_layer, question_edge), user_neighbors[layer_no -1],
                    self.Valuemiddle(question_layer_value, question_edge_value))

                user_neighbors_value_list[layer_no - 1] = self.u_node_generate(user_neighbors_value_list[layer_no - 1],
                                                                               question_neighbor_feature )
        #score edge strength
        #ATTENTION: remove user feature
        answer_value = self.a_edge_generate(
            question_neighbors[0], user_neighbors[0], answer_lstm_embed,
            question_neighbors_value_list[0], user_neighbors_value_list[0], answer_value
        )
        question_vec = torch.cat((question_neighbors[0], question_neighbors_value_list[0]), dim=-1)
        user_vec = torch.cat((user_neighbors[0], user_neighbors_value_list[0]), dim=-1)
        answer_vec = torch.cat((answer_lstm_embed, answer_value), dim=-1)
        # question_vec = question_neighbors_value_list[0]
        # answer_vec = answer_value
        # user_vec = user_neighbors_value_list[0]
        # question_vec = self.dropout(question_vec)
        # user_vec = self.dropout(user_vec)
        # answer_vec = self.dropout(answer_vec)

        score = self.score_fn(question_vec, answer_vec, user_vec)
        if self.args.is_classification:
            score = F.log_softmax(score, dim=-1)
            predic = torch.argmax(score, dim=-1)
            return_list = [score, predic]
        else:
            return_list = [score]
        # if need_feature:
        #     answer_vec = answer_edge_feaure.detach()
        #     return_list.append(answer_vec)
        return tuple(return_list)


        #
        # if self.training or not self.need_diversity:
        #     if self.args.is_classification:
        #         if predic == -1:
        #             exit(-1)
        #         return score, predic
        #     else:
        #         return score
        # else:
        #     feature_matrix = self.w_a(answer_edge_feaure) + self.w_q(question_neighbors[0]) + self.w_u(user_neighbors[0])
        #     candidate_answer_list = []
        #     temp = 0
        #     for i in count_list:
        #         feature_sub_matrix = feature_matrix[temp:temp + i]
        #         relevance_sub_list = score[temp:temp+i]
        #         candidate_answer_index = self.diversity_recomend(feature_sub_matrix, relevance_sub_list)
        #         candidate_answer_id_order = answer_edge[candidate_answer_index]
        #         candidate_answer_list.append(candidate_answer_id_order)
        #     if self.args.is_classification:
        #         #tensor, tensor, numpy, numpy
        #         return score, predic, tensorTonumpy(question,self.args.gpu), candidate_answer_list



