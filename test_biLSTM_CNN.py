import argparse
from tqdm import tqdm
#pytorch import
from Util import *

from biLSTM_CNN.Model import BiLstMCNN

from DataSet.dataset import rankDataOrdinary, my_clloect_fn_train, classify_collect_fn, classifyDataOrdinary
from Metric.coverage_metric import *
from Metric.rank_metrics import ndcg_at_k, average_precision, precision_at_k, mean_reciprocal_rank, Accuracy, marcoF1
from Config import config_model
import os
# os.chdir("/home/yichuan/course/induceiveAnswer")
# os.chdir("/home/weiying/yichuan/InduciveAnswer")

import resource
rlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (2048, rlimit[1]))

#grid search for paramter
from Visualization.logger import Logger

info = {}
log_filename = "./logs_bilstm"
if os.path.isdir(log_filename) is False:
    os.mkdir(log_filename)
filelist = [ f for f in os.listdir(log_filename)]
for f in filelist:
    os.remove(os.path.join(log_filename, f))
logger = Logger(log_filename)
logger = Logger(log_filename)
i_flag = 0
train_epoch_count = 0
eval_epoch_count = 0

#WARNNING: cannot output label, can only output score
def prepare_dataloaders(data, args):
    # ========= Preparing DataLoader =========#
    train_data = data['question_answer_user_train']
    test_data = data['question_answer_user_test']
    question_count = data['question_count']
    user_count = data['user_count']
    content_embed = ContentEmbed(data['content'])
    answer_score = data['vote_sort']
    answer_user_dic = data['answer_user_dic']

    if args.is_classification:
        train_loader = torch.utils.data.DataLoader(
            classifyDataOrdinary(
                args=args,
                question_answer_user_vote=train_data,
                content=content_embed,
                user_count=user_count
            ),
            num_workers=4,
            batch_size=args.batch_size,
            collate_fn=classify_collect_fn,
            shuffle=True
        )

        val_loader = torch.utils.data.DataLoader(
            classifyDataOrdinary(
                args=args,
                question_answer_user_vote=test_data,
                content=content_embed,
                user_count=user_count
            ),
            num_workers=4,
            batch_size=args.batch_size,
            collate_fn=classify_collect_fn,
            shuffle=True
        )
    else:
        train_loader = torch.utils.data.DataLoader(
        rankDataOrdinary(
                args=args,
                question_answer_user_vote=train_data,
                is_training=True,
                user_count=user_count,
                answer_score=answer_score,
                content_embed= content_embed,
                question_count=question_count,
            ),
            num_workers=4,
            batch_size=args.batch_size,
            shuffle=True,
        collate_fn = my_clloect_fn_train
        )

        val_loader = torch.utils.data.DataLoader(
        rankDataOrdinary(
                args=args,
                question_answer_user_vote=test_data,
                is_training=False,
                content_embed=content_embed,
                user_count=user_count,
                question_count=question_count,
                is_Multihop=False
            ),
            num_workers=4,
            batch_size=args.batch_size,
            shuffle=True,
            collate_fn = classify_collect_fn
        )

    return train_loader, val_loader




def train_epoch(model, data, optimizer, args, train_epoch_count):
    model.train()
    loss_fn =nn.NLLLoss() if args.is_classification else PairWiseHingeLoss(args.margin)
    line = 0
    loss1 = 0
    for batch in tqdm(
        data, mininterval=2, desc=' --(training)--',leave=True
    ):
        if args.is_classification:
            question_list, answer_list, gt_list, _ = map(lambda x: x.to(args.device), batch)
            args.batch_size = question_list.shape[0]
            line += args.batch_size
            optimizer.zero_grad()
            result, _ = model(question_list, answer_list)
            loss = loss_fn(result, gt_list)
        else:
            question_list, answer_pos_list, answer_neg_post = map(lambda x: x.to(args.device), batch)
            args.batch_size = question_list.shape[0]
            line += args.batch_size
            optimizer.zero_grad()
            good_score = model(question_list, answer_pos_list)
            bad_score = model(question_list, answer_neg_post)
            loss = loss_fn(good_score, bad_score)
        loss1 += loss.item()
        loss.backward()
        optimizer.step()

    # train_epoch_count += 1

    loss1 = loss1 / line
    logger.scalar_summary("train_loss", loss1, train_epoch_count)
    for tag, value in model.named_parameters():
        if value.grad is None:
            continue
        tag = tag.replace('.', '/')
        logger.histo_summary(tag, value.cpu().detach().numpy(), train_epoch_count)
        logger.histo_summary(tag + '/grad', value.grad.cpu().numpy(),train_epoch_count)



def eval_epoch(model, data, args, eval_epoch_count):
    model.eval()
    diversity_answer_recommendation = []
    questionid_answer_score_gt_dic = {}
    info_test = {}
    line_count = 0
    predic_list = []
    gt_list = []
    with torch.no_grad():
        for batch in tqdm(
            data, mininterval=2, desc="  ----(validation)----  ", leave=True
        ):

            q_val, a_val, gt_val, question_id_list = map(lambda x: x.to(args.device), batch)
            args.batch_size = gt_val.shape[0]
            line_count += gt_val.shape[0]

            question_id_list = tensorTonumpy(question_id_list, args.cuda)

            if args.is_classification:
                score,predic = model(q_val, a_val, is_training=False)
                score = tensorTonumpy(score[:,1], args.cuda)
                gt_val = tensorTonumpy(gt_val, args.cuda)
                predic = tensorTonumpy(predic, args.cuda)
                gt_list += gt_val.tolist()
                predic_list += predic.tolist()
                for questionid, gt, pred_score in zip(question_id_list, gt_val, score):
                    if questionid in questionid_answer_score_gt_dic:
                        questionid_answer_score_gt_dic[questionid].append([pred_score, gt])
                    else:
                        questionid_answer_score_gt_dic[questionid] = [[pred_score, gt]]


            else:
                score = model(q_val, a_val, is_training=False)
                score = tensorTonumpy(score, args.cuda)
                gt_val = tensorTonumpy(gt_val, args.cuda)
                a_val = tensorTonumpy(a_val, args.cuda)
                for questionid, answer_content, gt, pred_score in zip(question_id_list, a_val, gt_val, score):
                    if questionid in questionid_answer_score_gt_dic:
                        questionid_answer_score_gt_dic[questionid].append([answer_content, pred_score, gt])
                    else:
                        questionid_answer_score_gt_dic[questionid] = [[answer_content, pred_score, gt]]

    mAP = 0
    mRP = 0
    p_at_one = 0
    ndcg_loss = 0

    for _, values in questionid_answer_score_gt_dic.items():
        #biggest in the begining
        answer_score_gt_reorder = sorted(values, key=lambda x: -x[-2])
        rank_gt = [line[-1] for line in answer_score_gt_reorder]
        if args.is_classification:
           mAP += average_precision(rank_gt)
           mRP += mean_reciprocal_rank([rank_gt])
           p_at_one += precision_at_k([rank_gt], args.precesion_at_k)
        else:
            rank_answer_content = [line[0] for line in answer_score_gt_reorder]
            diversity_answer_recommendation.append(rank_answer_content)
            ndcg_loss += ndcg_at_k(rank_gt, args.ndcg_k)
            if np.argmax(rank_gt) == 0:
                p_at_one += 1
    question_count = len(questionid_answer_score_gt_dic)


    if args.is_classification:
        mAP = mAP*1.0 / question_count
        p_at_one = p_at_one*1.0 / question_count
        mRP = mRP *1.0 / question_count
        f1_score = marcoF1(y_gt=gt_list, y_pred=predic_list)
        accuracy, one_count, zero_count = Accuracy(label=gt_list, predict=predic_list)
        accuracy = accuracy * 1.0 / (one_count + zero_count)
        # visualize the data
        info_test['mAP'] = mAP
        info_test['P@1'] = p_at_one
        info_test['mRP'] = mRP
        info_test['acc'] = accuracy
        info_test['f1'] = f1_score
        print("[Info] mAP: {}, P@1: {}, mRP: {}, acc: {}, f1: {}".format(mAP, p_at_one, mRP, accuracy, f1_score))

    else:
        p_at_one = p_at_one * 1.0 / question_count
        ndcg_loss = ndcg_loss * 1.0 / question_count
        info_test['nDCGG'] = ndcg_loss
        info_test['P@1'] = p_at_one
        print("[INFO] Ranking Porblem nDCGG: {}, p@1 is {}".format(ndcg_loss, p_at_one))

    eval_epoch_count += 1


    for tag, value in info_test.items():
        logger.scalar_summary(tag, value, eval_epoch_count)

    return diversity_answer_recommendation








def train(args, train_data, val_data ,pre_trained_word2vec, content):
    model = BiLstMCNN(args, pre_trained_word2vec)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    model.to(args.device)
    #load coverage model
    if args.is_classification is False:
        cov_model_path = args.cov_model_path + "AMRNL"
        tfidf = TFIDFSimilar(content, False, cov_model_path)
        lda = LDAsimilarity(content, args.lda_topic, False, cov_model_path)
    info_val = {}
    for epoch_i in range(args.epoch):

        train_epoch(model, train_data, optimizer, args, epoch_i)

        diversity_answer_recommendation = eval_epoch(model, val_data, args, eval_epoch_count)
        if args.is_classification is False:
            tfidf_cov, lda_cov = diversity_evaluation(diversity_answer_recommendation, args.div_topK, tfidf, lda)

            info_val['tfidf_cov'] = tfidf_cov
            info_val['lda_cov'] = lda_cov
            print("[INFO] tfidf coverage {}, lda coverage {}".format(tfidf_cov, lda_cov))
        for tag, value in info_val.items():
            logger.scalar_summary(tag, value, eval_epoch_count)



def main():

    #===========Load DataSet=============#
    datafoler = "data/"
    #,"tex.torchpickle", "apple.torchpickle", "math.torchpickle"
    datasetname = ["store_SemEval.torchpickle"]
    args = config_model
    for datan in datasetname:
        args.is_classification = True if "SemEval" in datan else False
        args.data = datafoler + datan
        print("[FILE] Data file {}".format(args.data))
        print("cuda : {}".format(args.cuda))
        data = torch.load(args.data)
        word2ix = data['dict']
        content = data['content']
        love_list_count = data['love_list_count']
        user_count = data['user_count']
        print(user_count)
        train_data, val_data = prepare_dataloaders(data, args)
        pre_trained_word2vec = loadEmbed(args.embed_fileName, args.embed_size, args.vocab_size, word2ix, args.DEBUG).to(args.device)
        paragram_dic = {"lstm_hidden_size": [128],
                        "lstm_num_layers": [1, 2],
                        "drop_out_lstm": [0, 0.3],
                        "lr": [1e-4, 5e-4],
                        "run times":[1, 2, 3, 4, 5]
                        }
        pragram_list = grid_search(paragram_dic)
        for paragram in pragram_list:
            for key, value in paragram.items():
                print("Key: {}, Value: {}".format(key, value))
                setattr(args, key, value)
            train(args, train_data, val_data, pre_trained_word2vec, content)
if __name__ == '__main__':
    main()
