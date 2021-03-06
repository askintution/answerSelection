
import torch.utils.data as data
import numpy as np
import torch
from Constants import Constants
from random import shuffle
import itertools
from scipy.stats import rankdata


def context_collect_fn_train(batch):
    question_list = torch.LongTensor([item[0] for item in batch])
    answer_pos_list = torch.LongTensor([item[1] for item in batch])
    user_pos_list = torch.LongTensor([item[2] for item in batch])
    score_pos_list = torch.FloatTensor([item[3] for item in batch])
    answer_neg_list = torch.LongTensor([item[4] for item in batch])
    user_neg_list = torch.LongTensor([item[5] for item in batch])
    return question_list, answer_pos_list, user_pos_list, score_pos_list, answer_neg_list, user_neg_list

def context_collect_fn_test(batch):
    question_list = torch.LongTensor([item[0] for item in batch])
    answer_pos_list = torch.LongTensor([item[1] for item in batch])
    user_pos_list = torch.LongTensor([item[2] for item in batch])
    score_pos_list = torch.FloatTensor([item[3] for item in batch])
    question_id_list = torch.LongTensor([item[4] for item in batch])
    return question_list, answer_pos_list, user_pos_list, score_pos_list, question_id_list


def my_clloect_fn_train(batch):
    question_content, answer_pos_content, answer_neg_list = list(zip(*batch))
    question_content = torch.LongTensor(question_content)
    answer_pos_content = torch.LongTensor(answer_pos_content)
    answer_neg_list = torch.LongTensor(answer_neg_list)
    return (question_content, answer_pos_content, answer_neg_list)

def my_collect_fn_test(batch):
    question_content, answer_pos_content, score_pos_list, question_id = list(zip(*batch))
    question_content = torch.LongTensor(question_content)
    answer_pos_content =torch.LongTensor(answer_pos_content)
    score_pos_list = torch.FloatTensor(score_pos_list)
    question_id = torch.LongTensor(question_id)
    return (question_content, answer_pos_content, score_pos_list, question_id)

def my_collect_fn_train_hybrid(batch):
    question_content, answer_content, user_context, score, neg_ans_content, \
    neg_user_context = list(zip(*batch))
    question_content = torch.LongTensor(question_content)
    answer_content = torch.LongTensor(answer_content)
    user_context = torch.LongTensor(user_context)
    score = torch.FloatTensor(score)
    neg_ans_content = torch.LongTensor(neg_ans_content)
    neg_user_context = torch.LongTensor(neg_user_context)
    return question_content, answer_content, user_context, score, neg_ans_content, \
    neg_user_context



def my_collect_fn_test_hybrid(batch):
    question_content, answer_content, user_context, score, question_id = list(zip(*batch))
    question_content = torch.LongTensor(question_content)
    answer_content = torch.LongTensor(answer_content)
    user_context = torch.LongTensor(user_context)
    score = torch.FloatTensor(score)
    question_id = torch.LongTensor(question_id)
    return question_content, answer_content, user_context, score, question_id

# def my_collect_fn_test(batch):
#
#     batch = [item for item in batch if item[-1][0] > 5]
#
#     question_list = torch.LongTensor(list(itertools.chain.from_iterable([item[0]for item in batch])))
#     answer_list = torch.LongTensor(list(itertools.chain.from_iterable([item[1] for item in batch])))
#     user_list = torch.LongTensor([x for item in batch for x in item[2]])
#     score_list = torch.FloatTensor(list(itertools.chain.from_iterable([item[3] for item in batch])))
#     count_list = torch.IntTensor(list(itertools.chain.from_iterable([item[4] for item in batch])))
#     return question_list, answer_list, user_list, score_list, count_list

def classify_collect_fn(batch):
    question_content, answer_pos_content, score_pos_list, question_id = list(zip(*batch))
    question_content = torch.LongTensor(question_content)
    answer_pos_content = torch.LongTensor(answer_pos_content)
    label_list = torch.LongTensor(score_pos_list)
    question_id = torch.LongTensor(question_id)
    return (question_content, answer_pos_content, label_list, question_id)

def classify_collect_fn_hybrid(batch):
    question_content, answer_content, user_context, label, question_id = list(zip(*batch))
    question_content = torch.LongTensor(question_content)
    answer_content = torch.LongTensor(answer_content)
    user_context = torch.LongTensor(user_context)
    label_list = torch.LongTensor(label)
    question_id = torch.LongTensor(question_id)
    return question_content, answer_content, user_context, label_list, question_id

def classify_collect_fn_Nei(batch):
    q_iter, question_key, question_neighbor, question_neighbor_key, a_iter, u_iter, gt_iter = list(zip(*batch))
    q_iter = torch.LongTensor(q_iter)
    question_key = torch.FloatTensor(question_key)
    question_neighbor = torch.LongTensor(question_neighbor)
    question_neighbor_key = torch.FloatTensor(question_neighbor_key)
    a_iter = torch.LongTensor(a_iter)
    u_iter = torch.LongTensor(u_iter)
    gt_iter = torch.LongTensor(gt_iter)
    return q_iter, question_key, question_neighbor, question_neighbor_key, a_iter, u_iter, gt_iter


class rankDataNei(data.Dataset):
    def __init__(self,
                 args,
                 question_answer_user_vote_cate,
                 question_neighbor_finder,
                 answer_score,
                 user_count,
                 question_count,
                 is_training=False,
                 answer_user_dic=None
                 ):
        super(rankDataNei, self).__init__()
        self.args = args
        self.question_answer_user_vote_cate = question_answer_user_vote_cate
        self.question_neighbor_finder = question_neighbor_finder
        self.user_count = user_count
        self.k = args.k_neighbor
        self.question_count = question_count
        self.answer_score = answer_score
        self.answer_index_sort = self.rankAnswer(answer_score)
        self.is_training = is_training
        self.answer_user_dic = answer_user_dic

    def findSimCate(self, cate_index):
        same_cate = self.question_answer_user_vote_cate[self.question_answer_user_vote_cate[:,-1] == cate_index][:,0]

        return same_cate

    def nearestNeighbor(self, neighbors, index):
        distance_list = [self.question_neighbor_finder.get_distance(index, i) for i in neighbors]
        sort_index = np.argsort(distance_list)
        if len(sort_index) < self.k:
            result = neighbors[sort_index]
            more = self.k - len(sort_index)
            result = np.append(result, self.question_neighbor_finder.find_by_index(index, more))
        else:
            result = neighbors[sort_index[:self.k]]
        return result

    def rankAnswer(self, answer_score):
        # small in the begin
        rank_answer_index = np.argsort(answer_score)
        return rank_answer_index

    def negative_sampling(self, answerid):
        answerid = answerid - self.user_count - self.question_count
        locate = np.where(self.answer_index_sort == answerid)[0][0]
        if locate > self.args.neg_size:
            negative_answer = np.random.choice(list(range(locate)), self.args.neg_size, replace=False)
        else:
            negative_answer = np.random.choice(list(range(len(self.answer_score))), self.args.neg_size, replace=False)
        negative_answer = negative_answer[0]
        return negative_answer + self.user_count + self.question_count


    def __len__(self):
        return len(self.question_answer_user_vote_cate)

    def __getitem__(self, index):
        question_answer_vote_line = self.question_answer_user_vote_cate[index]
        question_id = question_answer_vote_line[0]
        question_key = self.question_neighbor_finder.get_item(question_id - self.user_count)
        sam_cateory = self.findSimCate(question_answer_vote_line[4])
        question_neighbor = self.nearestNeighbor(sam_cateory - self.user_count, question_id - self.user_count)
        # question_neighbor = self.question_neighbor_finder.find_by_index(question_id - self.user_count, self.k)
        question_neighbor_feature = [self.question_neighbor_finder.get_item(i) for i in question_neighbor]
        question_neighbor = [item + self.user_count for item in question_neighbor]


        answer_id = question_answer_vote_line[1]
        user_id = question_answer_vote_line[2]

        if self.is_training:
            negative_answer_id = self.negative_sampling(answer_id)
            negative_user_id = self.answer_user_dic[negative_answer_id]

            return question_id, question_key, question_neighbor, question_neighbor_feature, answer_id, user_id, negative_answer_id, \
                   negative_user_id
        else:
            return question_id,  question_key,  question_neighbor, question_neighbor_feature, answer_id, user_id




class classifyDataNei(data.Dataset):
    def __init__(self,
                 args,
                 question_answer_user_vote_cate,
                 question_neighbor_finder,
                 user_count
                 ):
        self.args = args
        self.question_answer_user_vote_cate = question_answer_user_vote_cate
        self.question_neighbor_finder = question_neighbor_finder
        self.user_count = user_count
        self.k = args.k_neighbor

    def findSimCate(self, cate_index):
        same_cate = self.question_answer_user_vote_cate[self.question_answer_user_vote_cate[:,-1] == cate_index][:,0]

        return same_cate

    def nearestNeighbor(self, neighbors, index):
        distance_list = [self.question_neighbor_finder.get_distance(index, i) for i in neighbors]
        sort_index = np.argsort(distance_list)
        if len(sort_index) < self.k:
            result = neighbors[sort_index]
            more = self.k - len(sort_index)
            result = np.append(result, self.question_neighbor_finder.find_by_index(index, more))
        else:
            result = neighbors[sort_index[:self.k]]
        return result

    def __len__(self):
        return len(self.question_answer_user_vote_cate)

    def __getitem__(self, index):
        question_answer_vote_line = self.question_answer_user_vote_cate[index]
        question_id = question_answer_vote_line[0]
        question_key = self.question_neighbor_finder.get_item(question_id - self.user_count)
        sam_cateory = self.findSimCate(question_answer_vote_line[4])
        question_neighbor = self.nearestNeighbor(sam_cateory - self.user_count, question_id - self.user_count)
        # question_neighbor = self.question_neighbor_finder.find_by_index(question_id - self.user_count, self.k)
        question_neighbor_feature = [self.question_neighbor_finder.get_item(i) for i in question_neighbor]
        question_neighbor = [item + self.user_count for item in question_neighbor]


        answer_id = question_answer_vote_line[1]
        user_id = question_answer_vote_line[2]
        label = question_answer_vote_line[3]

        return question_id,  question_key,  question_neighbor, question_neighbor_feature, answer_id, user_id, label




class classifyDataEdge(data.Dataset):
    def __init__(self,
                 args,
                 question_answer_user_vote
                 ):
        self.args = args
        self.question_answer_user_vote = question_answer_user_vote

    def __len__(self):
        return len(self.question_answer_user_vote)

    def __getitem__(self, index):
        question_answer_vote_line = self.question_answer_user_vote[index]
        question_id = question_answer_vote_line[0]
        answer_id = question_answer_vote_line[1]
        user_id = question_answer_vote_line[2]
        label = question_answer_vote_line[3]
        return question_id, answer_id, user_id, label

class classifyDataSetEdge(data.Dataset):
    def __init__(self,
                 G,
                 args,
                 is_training=True
                 ):
        self.G = G
        self.args = args
        self.is_training = is_training
        self.edges = self.edgeGenre()

    def edgeGenre(self):
        edges = []
        for edge in self.G.edges(data=True):
            train_removed = edge[2]['train_removed']
            if (self.is_training is True) and (train_removed is False):
                edges.append(edge)
            elif (self.is_training is False) and (train_removed is True):
                edges.append(edge)
        return edges

    def __len__(self):
        return len(self.edges)

    def __getitem__(self, edgeidx):
        edge = self.edges[edgeidx]
        questionId = edge[0] if edge[0] > edge[1] else edge[1]
        userId = edge[1] if edge[0] > edge[1] else edge[0]

        answerId = edge[2]['a_id']
        label = edge[2]['score']
        return questionId, answerId, userId, label

class rankDataSetEdge(data.Dataset):
    def __init__(self,
                 G,
                 args,
                 answer_score,
                 question_count,
                 user_count,
                 answer_user_dic,
                 is_training=True
                 ):
        self.G = G
        self.args = args
        self.is_training = is_training
        self.user_count = user_count
        self.question_count = question_count
        self.answer_score = answer_score
        self.answer_user_dic = answer_user_dic
        self.answer_index_sort = self.rankAnswer(answer_score)
        self.edges = self.edgeGenre()

    def edgeGenre(self):
        edges = []
        for edge in self.G.edges(data=True):
            train_removed = edge[2]['train_removed']
            if self.is_training and ~train_removed:
                edges.append(edge)
            elif ~self.is_training and train_removed:
                edges.append(edge)
        return edges

    def rankAnswer(self, answer_score):
        # small in the begin
        rank_answer_index = np.argsort(answer_score)
        return rank_answer_index

    def negative_sampling(self, answerid):
        answerid = answerid - self.user_count - self.question_count
        locate = np.where(self.answer_index_sort == answerid)[0][0]
        if locate > self.args.neg_size:
            negative_answer = np.random.choice(list(range(locate)), self.args.neg_size, replace=False)
        else:
            negative_answer = np.random.choice(list(range(len(self.answer_score))), self.args.neg_size, replace=False)
        negative_answer = negative_answer[0]
        return negative_answer + self.user_count + self.question_count

    def __len__(self):
        return len(self.edges)

    def __getitem__(self, edgeidx):
        edge = self.edges[edgeidx]
        questionId = edge[0] if edge[0] > edge[1] else edge[1]
        userId = edge[1] if edge[0] > edge[1] else edge[0]

        answerId = edge[2]['a_id']
        score = edge[2]['score']
        if self.is_training:
            neg_ans = self.negative_sampling(answerId)
            neg_user = self.answer_user_dic[neg_ans]

            return questionId, answerId, userId, score, neg_ans, neg_user

        else:
            return questionId, answerId, userId, score

class classifyDataOrdinary(data.Dataset):
    def __init__(self,
                 args,
                 question_answer_user_vote,
                 content,
                 user_count,
                 ):
        self.args = args
        self.content = content
        self.question_answer_user_vote = question_answer_user_vote
        self.user_count = user_count

    def __len__(self):
        return len(self.question_answer_user_vote)

    def __getitem__(self, index):
        question_answer_vote_line = self.question_answer_user_vote[index]
        question_id = question_answer_vote_line[0]
        answer_id = question_answer_vote_line[1]
        answer_content = self.content.content_embed(answer_id - self.user_count)
        question_content = self.content.content_embed(question_id - self.user_count)
        label = question_answer_vote_line[3]
        return question_content, answer_content, label, question_id

class rankDataOrdinary(data.Dataset):

    def __init__(self,
                 args,
                 question_answer_user_vote,
                 content_embed,
                 question_count,
                 user_count,
                 answer_score=None,
                 is_training=True,
                 is_Multihop=False
                 ):
        self.args = args
        self.content = content_embed
        self.question_answer_user_vote = question_answer_user_vote

        self.user_count = user_count
        self.question_count = question_count
        self.is_training = is_training
        self.is_Multihop = is_Multihop
        if self.is_training:
            self.answer_score = answer_score
            self.answer_index_sort = self.rankAnswer(answer_score)

    def rankAnswer(self, answer_score):
        # small in the begin
        rank_answer_index = np.argsort(answer_score)
        return rank_answer_index

    def negative_sampling(self, answerid):
        # rank = self.rank_score[answerid - self.user_count - self.question_count]
        # negative_answer_candidate = self.rank_index[:rank]
        answerid = answerid - self.user_count - self.question_count
        locate = np.where(self.answer_index_sort == answerid)[0][0]
        if locate > self.args.neg_size and self.is_Multihop is False:
            negative_answer = np.random.choice(list(range(locate)), self.args.neg_size, replace=False)
        else:
            negative_answer = np.random.choice(list(range(len(self.answer_score))), self.args.neg_size, replace=False)
        negative_answer = negative_answer[0]
        return negative_answer + self.user_count + self.question_count


    def __len__(self):
        return len(self.question_answer_user_vote)

    def __getitem__(self, index):
        question_answer_vote_line = self.question_answer_user_vote[index]
        question_id = question_answer_vote_line[0]
        answer_id = question_answer_vote_line[1]
        answer_content = self.content.content_embed(answer_id - self.user_count)
        question_content = self.content.content_embed(question_id - self.user_count)
        pos_score = question_answer_vote_line[3]
        if self.is_training:
            neg_ans = self.negative_sampling(answer_id)
            neg_ans_content = self.content.content_embed(neg_ans - self.user_count)

            return question_content, answer_content, neg_ans_content
        else:
            return question_content, answer_content, pos_score, question_id






class classifyDataSetUserContext(data.Dataset):
    def __init__(self,
                 args,
                 question_answer_user_vote,
                 content_embed,
                 user_count,
                 is_hybrid=False,
                 user_context=None
                 ):
        self.args = args
        self.user_context = user_context
        self.content_embed = content_embed
        self.user_count = user_count
        self.question_answer_user_vote = question_answer_user_vote
        self.is_hybrid = is_hybrid


    def get_user_context(self, userid):
        document = []
        for answer_id in self.user_context[userid]:
            document += self.content_embed.content_embed(answer_id - self.user_count)
            if len(document) > self.args.max_u_len:
                document = document[:self.args.max_u_len]
                break
        if len(document) < self.args.max_u_len:
            pad_word = [Constants.PAD] * (self.args.max_u_len - len(document))
            document += pad_word
        return document


    def __len__(self):
        return len(self.question_answer_user_vote)

    def __getitem__(self, index):
        question_answer_vote_line = self.question_answer_user_vote[index]
        question_id = question_answer_vote_line[0]
        answer_id = question_answer_vote_line[1]
        answer_content = self.content_embed.content_embed(answer_id - self.user_count)
        question_content = self.content_embed.content_embed(question_id - self.user_count)
        user_context = self.get_user_context(question_answer_vote_line[2]) if self.is_hybrid else question_answer_vote_line[2]
        label = question_answer_vote_line[3]

        return question_content, answer_content, user_context, label, question_id



class rankDataSetUserContext(data.Dataset):
    def __init__(self,
                 args,
                 question_answer_user_vote,
                 content_embed,
                 question_count,
                 user_count,
                 user_context=None,
                 is_training=True,
                 answer_score=None,
                 answer_user_dic=None,
                 is_hybrid=False
                 ):
        self.args = args
        self.user_context = user_context
        self.content_embed = content_embed
        self.is_training = is_training
        self.user_count = user_count
        self.question_count = question_count
        self.question_answer_user_vote = question_answer_user_vote
        self.answer_user_dic = answer_user_dic
        self.is_hybrid = is_hybrid
        if is_training:
            self.answer_score = answer_score
            self.answer_index_sort = self.rankAnswer(answer_score)



    def rankAnswer(self, answer_score):
        #small in the begin
        rank_answer_index = np.argsort(answer_score)
        return rank_answer_index

    def negative_sampling(self, answerid):
        # rank = self.rank_score[answerid - self.user_count - self.question_count]
        # negative_answer_candidate = self.rank_index[:rank]
        answerid = answerid - self.user_count - self.question_count
        locate = np.where(self.answer_index_sort == answerid)[0][0]
        if locate > self.args.neg_size:
            negative_answer = np.random.choice(list(range(locate)), self.args.neg_size, replace=False)
        else:
            negative_answer = np.random.choice(list(range(len(self.answer_score))), self.args.neg_size, replace=False)
        negative_answer = negative_answer[0]
        return negative_answer + self.user_count + self.question_count

    def get_user_context(self, userid):
        document = []
        for answer_id in self.user_context[userid]:
            document += self.content_embed.content_embed(answer_id - self.user_count)
            if len(document) > self.args.max_u_len:
                document = document[:self.args.max_u_len]
                break
        if len(document) < self.args.max_u_len:
            pad_word = [Constants.PAD] * (self.args.max_u_len - len(document))
            document += pad_word
        return document


    def __len__(self):
        return len(self.question_answer_user_vote)

    def __getitem__(self, index):
        question_answer_vote_line = self.question_answer_user_vote[index]
        question_id = question_answer_vote_line[0]
        answer_id = question_answer_vote_line[1]
        answer_content = self.content_embed.content_embed(answer_id - self.user_count)
        question_content = self.content_embed.content_embed(question_id - self.user_count)
        user_context = self.get_user_context(question_answer_vote_line[2]) if self.is_hybrid else question_answer_vote_line[2]
        score = question_answer_vote_line[3]
        if self.is_training:
            neg_ans = self.negative_sampling(answer_id)
            neg_ans_content = self.content_embed.content_embed(neg_ans - self.user_count)
            neg_user_context = self.get_user_context(self.answer_user_dic[neg_ans]) if self.is_hybrid else self.answer_user_dic[neg_ans]

            return question_content, answer_content, user_context, score, neg_ans_content, neg_user_context
        else:
            return question_content, answer_content, user_context, score, question_id







class rankData(data.Dataset):
    def __init__(self,
                 G,
                 args,
                 answer_score,
                 question_answer_user_vote,
                 content,
                 question_count=None,
                 user_context=None,
                 user_count=None,
                 is_training=True,
                 answer_user_dic=None
                 ):
        self.args = args
        self.user_context = user_context
        self.content = content
        self.is_training = is_training
        self.user_count = user_count
        self.question_count = question_count
        self.question_answer_user_vote = question_answer_user_vote
        self.answer_user_dic = answer_user_dic
        self.answer_score = answer_score
        self.rank_score, self.rank_index = self.rankAnswer(answer_score)



    def rankAnswer(self, answer_score):
        rank_score = [int(i) for i in rankdata(answer_score, method='ordinal')]
        rank_dic = {rank:index for index, rank in enumerate(rank_score) }
        rank_index = [ index for _, index in  sorted(rank_dic.items(), key=lambda x: x[0])]
        return rank_score, rank_index

    def negative_sampling(self, answerid):
        rank = self.rank_score[answerid - self.user_count - self.question_count]
        negative_answer_candidate = self.rank_index[:rank]
        negative_score = self.answer_score[self.rank_index[:rank]]
        negative_pro = negative_score / np.sum(negative_score)
        if len(negative_answer_candidate) > self.args.neg_size:
            negative_answer = np.random.choice(negative_answer_candidate, self.args.neg_size, replace=False, p=negative_pro)
        else:
            negative_answer = np.random.choice(list(range(len(self.answer_score))), self.args.neg_size, replace=False, p=self.answer_score/np.sum(self.answer_score))

        return negative_answer + self.user_count + self.question_count

    def random_negative(self, questionId, userId, score):

        user_list = [user for user in self.G.neighbors(questionId) if self.G[questionId][user]['score'] < score]
        if len(user_list) < 1:
            return -1
        while (user_list[0] == userId):
            shuffle(user_list)

        return user_list[0]





    def __len__(self):

        return len(self.question_answer_user_vote)

    def __getitem__(self, idx):
        question_list = []
        answer_pos_list = []
        user_pos_list = []
        score_pos_list = []

        answer_neg_list = []
        user_neg_list = []
        score_neg_list = []
        #1
        question = self.question_id_list[idx]
        # k * 1
        user_list = list(self.G.neighbors(question))

        #generate negative answer
        for user_pos in user_list:
            #ATTENTION: people answer the same question for multiple times
            answer_pos = self.G[question][user_pos]['a_id']
            score_pos = self.G[question][user_pos]['score']


            if self.is_training:
                user_neg = self.random_negative(question, user_pos, score_pos)
                if(user_neg == -1):
                    continue
                answer_n = self.G[question][user_neg]['a_id']
                score_neg = self.G[question][user_neg]['score']
                answer_neg_list.append(answer_n)
                score_neg_list.append(score_neg)
                if self.user_context is not None:
                    document = []
                    for neg_id in self.user_context[user_neg]:
                        document += self.content.content_embed(neg_id - self.user_count)
                        if len(document) > self.args.max_u_len:
                            document = document[:self.args.max_u_len]
                            break
                    if len(document) < self.args.max_u_len:
                        pad_word = [Constants.PAD] * (self.args.max_u_len - len(document))
                        document += pad_word
                    user_neg_list.append(document)
                else:
                    user_neg_list.append(user_neg)

            question_list.append(question)
            answer_pos_list.append(answer_pos)
            if self.user_context is not None:
                document = []
                for post_id in self.user_context[user_pos]:
                    document += self.content.content_embed(post_id - self.user_count)
                    if len(document) > self.args.max_u_len:
                        document = document[:self.args.max_u_len]
                        break
                if len(document) < self.args.max_u_len:
                    pad_word = [Constants.PAD] * (self.args.max_u_len - len(document))
                    document += pad_word
                user_pos_list.append(document)
            else:
                user_pos_list.append(user_pos)
            score_pos_list.append(score_pos)

        if self.is_training:
            return question_list, answer_pos_list, user_pos_list, score_pos_list, answer_neg_list, user_neg_list, score_neg_list,[len(question_list)]
        else:
            return question_list, answer_pos_list, user_pos_list, score_pos_list, [len(question_list)]



# class clasifyDataSet(data.Dataset):
#
#     def __init__(self,
#                  data,
#                  question_finder
#                  ):
#         self.data = data
#         self.question_finder = question_finder
#
#     def __len__(self):
#         return len(self.data)
#
#     def __getitem__(self,   idx):
#         line = self.data[idx]
#         question_index = line[0]
#         answer_index = line[1]
#         user_index = line[2]
#         label = line[3]
#         users = self.G.neighbors(question_id)
#
#         question_list = []
#         user_list = []
#         label_list = []
#         answer_list = []
#         for user in users:
#             answer = self.G[question_id][user]['a_id']
#             label = self.G[question_id][user]['score']
#             question_list.append(question_id)
#             if self.user_context is not None:
#                 document = []
#                 for post_id in self.user_context[user]:
#                     document += self.content.content_embed(post_id - self.user_count)
#                     if len(document) > self.args.max_u_len:
#                         document = document[:self.args.max_u_len]
#                         break
#                 if len(document) < self.args.max_u_len:
#                     pad_word = [Constants.PAD] * (self.args.max_u_len - len(document))
#                     document += pad_word
#                 user_list.append(document)
#             else:
#                 user_list.append(user)
#             answer_list.append(answer)
#             label_list.append(label)
#
#         return question_list, answer_list, user_list, label_list, [len(question_list)]