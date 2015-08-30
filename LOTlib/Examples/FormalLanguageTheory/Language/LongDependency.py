from LOTlib.Examples.FormalLanguageTheory.Language.FormalLanguage import FormalLanguage
import itertools
from collections import Counter
from LOTlib.Miscellaneous import logsumexp
from Levenshtein import distance
from math import log


class LongDependency(FormalLanguage):

    def __init__(self, A='a', B='b', max_length=5):
        """
        NOTE: we specify the size of pool from which we will draw our X in sampling strings instead of max_length
        """
        assert len(A) == 1 and len(B) == 1, 'atom length should be one'

        self.A = A
        self.B = B
        self.C = ['c', 'd', 'e', 'f']

        FormalLanguage.__init__(self, max_length)

    def all_strings(self, max_length):

        assert max_length > 1, 'pool_size should be larger than 2'

        num = 0
        for e in list(itertools.product(*([self.C]*3))):
            num += 1
            if num > max_length: break
            yield self.A + self.t2s(e) + self.B

    def estimate_precision_and_recall(self, h, data):
        """
        Re-implementation: return how accurate the h is on predicting adjacent grammar
        """
        # TODO num of data is fixed
        # TODO use data for convenience
        num = 1024.0 / len(self.str_sets)
        output_t = {}
        for k in self.str_sets:
            output_t[self.de_ht(k)] = num

        # h_out = Counter([h() for _ in xrange(1024)])
        h_out = data
        h_out_t = {}
        for k, v in h_out.iteritems():
            h_out_t[self.de_ht(k)] = v

        base = sum(h_out_t.values())
        cnt = 0.0
        for k, v in h_out_t.iteritems():
            if k in output_t: cnt += v
        precision = cnt / base

        base = sum(output_t.values())
        cnt = 0.0
        for k, v in output_t.iteritems():
            if k in h_out_t: cnt += v
        recall = cnt / base

        return precision, recall

    def ht(self, s):
        """
        get head and tail of s
        """
        if s is None or len(s) < 2: return None
        return s[0] + s[-1]

    def de_ht(self, s):
        """
        remove head and tail of s
        """
        if s is None or len(s) < 2: return ''
        return s[1:-1]

    def t2s(self, t):
        s = ''
        for e in t:
            s += e
        return s


# just for testing
if __name__ == '__main__':
    language = LongDependency(max_length=4)

    # for e in language.all_strings(max_length=12):
    #     print e

    print language.sample_data_as_FuncData(128)
    # print language.is_valid_string('aaa')
    # print language.is_valid_string('ab')
    # print language.is_valid_string('abb')
    # print language.is_valid_string('aaab')
    # print language.is_valid_string('aabb')