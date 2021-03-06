import torch
import torch.nn.functional as F
import torch.nn as nn
from Util import LSTM_MeanPool


'''
Community-Based Question Answering via Asymmetric Multi-Faceted Ranking Network Learning
'''
class AMRNL(nn.Module):
    def __init__(self, args,
                 user_count,
                 word2vec,
                 user_adjance,
                 user_love_degree
                 ):
        super(AMRNL, self).__init__()
        hidden_size = (2 if args.bidirectional else 1) * args.lstm_hidden_size
        self.lstm_meanpool = LSTM_MeanPool(args)
        self.args = args
        self.user_count = user_count
        self.user_embed = nn.Embedding(self.user_count + 1, hidden_size, padding_idx=self.user_count)
        self.word2vec = nn.Embedding.from_pretrained(word2vec)
        #already normalized
        self.user_adjance_embed = user_adjance
        self.user_love_degree_embed = user_love_degree

        # f_M(q_i, u_j, a_k) = s_M(q_i, a_k)s(q_i, u_j)
        # s_M(q_i, a_k) = q_i * M * a_k => batch_size * 1 => batch of question answer match score

        self.smantic_mach_bilinear = nn.Bilinear(hidden_size, hidden_size, 1)
        self.question_weight = nn.Linear(args.lstm_hidden_size, args.lstm_hidden_size)
        self.answer_weight = nn.Linear(args.lstm_hidden_size, args.lstm_hidden_size)
        self.user_weight = nn.Linear(args.lstm_hidden_size, args.lstm_hidden_size)

        self.classify_weight = nn.Linear(args.lstm_hidden_size, args.num_class)
        # self.drop_out = nn.Dropout(args.drop_out_lstm)


    def forward(self,
                question_list,
                answer_list,
                user_list
                ):


        question_embed_feature = self.word2vec(question_list)
        answer_embed_feature = self.word2vec(answer_list)
        user_embed_feature = self.user_embed(user_list)

        question_lstm = self.lstm_meanpool(question_embed_feature)
        answer_lstm = self.lstm_meanpool(answer_embed_feature)
        # question_lstm = self.drop_out(question_lstm)
        # answer_lstm = self.drop_out(answer_lstm)


        # relevance_score = F.cosine_similarity(question_lstm, user_embed_feature, dim=-1)

        #l2 norm
        if self.args.is_classification is False:
            match_score = self.smantic_mach_bilinear(question_lstm, answer_lstm)
            # ATTENTION: In ARMNL they use (q_i).T * u_j as similarity between question and answer
            relevance_score = torch.sum(question_lstm * user_embed_feature, dim=-1, keepdim=True)
            score = match_score * relevance_score
            user_follow_feature = torch.sum(self.user_embed(self.user_adjance_embed.content_embed(user_list)), dim=-2) / (self.user_love_degree_embed.content_embed(user_list) + self.args.follow_smooth)
            regular = F.normalize(user_embed_feature - user_follow_feature, 2, dim=-1)
            return score, regular
        else:
            score = torch.tanh(self.question_weight(question_lstm) + self.answer_weight(answer_lstm) + self.user_weight(user_embed_feature))
            score = torch.softmax(self.classify_weight(score), dim=-1)
            predic = torch.argmax(score, dim =-1)
            return score, predic






