"""Information Retrieval metrics

Useful Resources:
http://www.cs.utexas.edu/~mooney/ir-course/slides/Evaluation.ppt
http://www.nii.ac.jp/TechReports/05-014E.pdf
http://www.stanford.edu/class/cs276/handouts/EvaluationNew-handout-6-per.pdf
http://hal.archives-ouvertes.fr/docs/00/72/67/60/PDF/07-busa-fekete.pdf
Learning to Rank for Information Retrieval (Tie-Yan Liu)
"""

# raw url: https://gist.github.com/bwhite/3726239
# raw url: https://blog.csdn.net/lujiandong1/article/details/77123805
import numpy as np
# from sklearn.metrics import average_precision_score as avg_sklearn
from scipy.stats import rankdata
from sklearn.metrics import f1_score

def marcoF1(y_gt, y_pred):
    return f1_score(y_true=y_gt,y_pred=y_pred, average="macro")

def mean_reciprocal_rank(rs):
    """Score is reciprocal of the rank of the first relevant item
    First element is 'rank 1'.  Relevance is binary (nonzero is relevant).
    Example from http://en.wikipedia.org/wiki/Mean_reciprocal_rank
    >>> rs = [[0, 0, 1], [0, 1, 0], [1, 0, 0]]
    >>> mean_reciprocal_rank(rs)
    0.61111111111111105
    >>> rs = np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]])
    >>> mean_reciprocal_rank(rs)
    0.5
    >>> rs = [[0, 0, 0, 1], [1, 0, 0], [1, 0, 0]]
    >>> mean_reciprocal_rank(rs)
    0.75
    Args:
        rs: Iterator of relevance scores (list or numpy) in rank order
            (first element is the first item)
    Returns:
        Mean reciprocal rank
    """
    rs = (np.asarray(r).nonzero()[0] for r in rs)
    return np.mean([1. / (r[0] + 1) if r.size else 0. for r in rs])


def r_precision(r):
    """Score is precision after all relevant documents have been retrieved

    Relevance is binary (nonzero is relevant).

    >>> r = [0, 0, 1]
    >>> r_precision(r)
    0.33333333333333331
    >>> r = [0, 1, 0]
    >>> r_precision(r)
    0.5
    >>> r = [1, 0, 0]
    >>> r_precision(r)
    1.0

    Args:
        r: Relevance scores (list or numpy) in rank order
            (first element is the first item)

    Returns:
        R Precision
    """
    r = np.asarray(r) != 0
    z = r.nonzero()[0]
    if not z.size:
        return 0.
    return np.mean(r[:z[-1] + 1])



def precision_at_k(r_list, k):
    """Score is precision @ k

    Relevance is binary (nonzero is relevant).

    >>> r_list = [[0, 0, 1],[0,0,1]]
    >>> precision_at_k(r_list, 1)
    0.0
    >>> precision_at_k(r_list, 2)
    0.0
    >>> precision_at_k(r_list, 3)
    0.33333333333333331
    >>> precision_at_k(r_list, 4)
    Traceback (most recent call last):
        File "<stdin>", line 1, in ?
    ValueError: Relevance score length < k


    Args:
        r: Relevance scores (list or numpy) in rank order
            (first element is the first item)

    Returns:
        Precision @ k

    Raises:
        ValueError: len(r) must be >= k
    """
    assert k >= 1
    scores = []
    for r in r_list:
        r = np.asarray(r)[:k] != 0
        if r.size != k:
            raise ValueError('Relevance score length < k')
        scores.append(np.mean(r))
    return np.mean(scores)



# def average_precision_scikit(y_true, y_score):
#     return avg_sklearn(y_true, y_score)
#
# def mean_average_precision_scikit(y_true_list, y_score_list):
#     result = np.array([average_precision_scikit(y_true, y_score) for y_true, y_score in zip(y_true_list, y_score_list)])
#     #WARNNING: remove nan
#     result = result[~np.isnan(result)]
#     return np.mean(result)




def average_precision_rank_score(label, rank_score):
    """
    Pay attention to the rank score order
    >>> r = [1, 0, 1, 0, 1]
    >>> score = [0.12, 0.15, 0.17]
    >>> index = np.argmax(score)
    >>> sorted_score = np.sort(score)
    :param r:
    :return:
    """
    rank_order = rankdata(rank_score)
    rank_order = [int(i) for i in rank_order]
    ap = 0
    for index, j in enumerate(rank_order):
        p_j = 0
        for i in range(j):
            p_j += label[rank_order[i] - 1]
        try:
            p_j = p_j * 1.0 / j * label[rank_order[j] - 1]
        except:
            print("hello")
        ap += p_j
    if np.sum(label) == 0:
        ap = 0
    else:
        ap = ap / np.sum(label)
    return ap



# def average_precision(label, rank_score):
#     """Score is average precision (area under PR curve)
#
#     Relevance is binary (nonzero is relevant).
#
#     >>> r = [1, 1, 0, 1, 0, 1, 0, 0, 0, 1]
#     >>> delta_r = 1. / sum(r)
#     >>> sum([sum(r[:x + 1]) / (x + 1.) * delta_r for x, y in enumerate(r) if y])
#     0.7833333333333333
#     >>> average_precision(r)
#     0.78333333333333333
#
#     Args:
#         r: Relevance scores (list or numpy) in rank order
#             (first element is the first item)
#
#     Returns:
#         Average precision
#     """
#     rank_score = np.asarray(rank_score)
#     label = np.array(label)
#     out = average_precision_rank_score(label, rank_score)
#     return out


# def mean_average_precision_yichuan(label_list, rank_score_list):
#     """Score is mean average precision
#     Relevance is binary (nonzero is relevant).
#     >>> rs = [[1, 1, 0, 1, 0, 1, 0, 0, 0, 1]]
#     >>> mean_average_precision(rs)
#     0.78333333333333333
#     >>> rs = [[1, 1, 0, 1, 0, 1, 0, 0, 0, 1], [0]]
#     >>> mean_average_precision(rs)
#     0.39166666666666666
#     Args:
#         rs: Iterator of relevance scores (list or numpy) in rank order
#             (first element is the first item)
#     Returns:
#         Mean average precision
#     """
#     return np.mean([average_precision(label, rank_score) for label, rank_score in zip(label_list, rank_score_list)])

def average_precision(r):
    """Score is average precision (area under PR curve)
    Relevance is binary (nonzero is relevant).
    >>> r = [1, 1, 0, 1, 0, 1, 0, 0, 0, 1]
    >>> delta_r = 1. / sum(r)
    >>> sum([sum(r[:x + 1]) / (x + 1.) * delta_r for x, y in enumerate(r) if y])
    0.7833333333333333
    >>> average_precision(r)
    0.78333333333333333
    Args:
        r: Relevance scores (list or numpy) in rank order
            (first element is the first item)
    Returns:
        Average precision
    """
    r = np.asarray(r) != 0
    out = [precision_at_k([r], k + 1) for k in range(r.size) if r[k]]
    if not out:
        return 0.
    return np.mean(out)

def mean_average_precision(rs):
    """Score is mean average precision
    Relevance is binary (nonzero is relevant).
    >>> rs = [[1, 1, 0, 1, 0, 1, 0, 0, 0, 1]]
    >>> mean_average_precision(rs)
    0.78333333333333333
    >>> rs = [[1, 1, 0, 1, 0, 1, 0, 0, 0, 1], [0]]
    >>> mean_average_precision(rs)
    0.39166666666666666
    Args:
        rs: Iterator of relevance scores (list or numpy) in rank order
            (first element is the first item)
    Returns:
        Mean average precision
    """
    return np.mean([average_precision(r) for r in rs])




def dcg_at_k(r, k, method=0):
    """Score is discounted cumulative gain (dcg)

    Relevance is positive real values.  Can use binary
    as the previous methods.

    Example from
    http://www.stanford.edu/class/cs276/handouts/EvaluationNew-handout-6-per.pdf
    >>> r = [3, 2, 3, 0, 0, 1, 2, 2, 3, 0]
    >>> dcg_at_k(r, 1)
    3.0
    >>> dcg_at_k(r, 1, method=1)
    3.0
    >>> dcg_at_k(r, 2)
    5.0
    >>> dcg_at_k(r, 2, method=1)
    4.2618595071429155
    >>> dcg_at_k(r, 10)
    9.6051177391888114
    >>> dcg_at_k(r, 11)
    9.6051177391888114

    Args:
        r: Relevance scores (list or numpy) in rank order
            (first element is the first item)
        k: Number of results to consider
        method: If 0 then weights are [1.0, 1.0, 0.6309, 0.5, 0.4307, ...]
                If 1 then weights are [1.0, 0.6309, 0.5, 0.4307, ...]

    Returns:
        Discounted cumulative gain
    """
    r = np.asfarray(r)[:k]
    if r.size:
        if method == 0:
            return r[0] + np.sum(r[1:] / np.log2(np.arange(2, r.size + 1)))
        elif method == 1:
            return np.sum(r / np.log2(np.arange(2, r.size + 2)))
        else:
            raise ValueError('method must be 0 or 1.')
    return 0.

def ndcg_at_k(r, k, method=0):
    """Score is normalized discounted cumulative gain (ndcg)

    Relevance is positive real values.  Can use binary
    as the previous methods.

    Example from
    http://www.stanford.edu/class/cs276/handouts/EvaluationNew-handout-6-per.pdf
    >>> r = [3, 2, 3, 0, 0, 1, 2, 2, 3, 0]
    >>> ndcg_at_k(r, 1)
    unknown
    >>> r = [[2, 1, 2, 0]]
    >>> ndcg_at_k(r, 4)
    unknwon
    >>> ndcg_at_k(r, 4, method=1)
    0.96519546960144276
    >>> ndcg_at_k([0], 1)
    0.0
    >>> ndcg_at_k([1], 2)
    1.0

    Args:
        r: Relevance scores (list or numpy) in rank order
            (first element is the first item)
        k: Number of results to consider
        method: If 0 then weights are [1.0, 1.0, 0.6309, 0.5, 0.4307, ...]
                If 1 then weights are [1.0, 0.6309, 0.5, 0.4307, ...]

    Returns:
        Normalized discounted cumulative gain
    """
    dcg_max = dcg_at_k(sorted(r, reverse=True), k, method)
    if not dcg_max:
        return 0.
    return dcg_at_k(r, k, method) / dcg_max


def Accuracy(label, predict):
    target = 0
    zero_count = 0
    one_count = 0
    assert len(predict) == len(label), "[ERROR] Length not equal"
    for i in range(len(predict)):
        if predict[i] == 0:
            zero_count += 1
        elif predict[i] == 1:
            one_count += 1
        if predict[i] == label[i]:
            target += 1
    return target, zero_count, one_count


if __name__ == "__main__":
    import doctest
    doctest.testmod()
