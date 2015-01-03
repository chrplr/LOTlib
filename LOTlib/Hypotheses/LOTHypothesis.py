
from copy import copy, deepcopy
from math import log
import numpy as np
from LOTlib.DataAndObjects import FunctionData
from LOTlib.Evaluation.Eval import evaluate_expression
from LOTlib.Evaluation.EvaluationException import TooBigException, EvaluationException
from LOTlib.Hypotheses.FunctionHypothesis import FunctionHypothesis
from LOTlib.Inference.Proposals.RegenerationProposal import RegenerationProposal
from LOTlib.Miscellaneous import Infinity, lambdaNone, raise_exception
from LOTlib.GrammarRule import BVUseGrammarRule


class LOTHypothesis(FunctionHypothesis):
    """A FunctionHypothesis built from a grammar.

    Arguments
    ---------
    grammar : LOTLib.Grammar
        The grammar for the hypothesis.
    value : FunctionNode
        The value for the hypothesis.
    f
        If specified, we don't recompile the whole function.
    start
        The start symbol for the grammar.
    ALPHA : float
        Parameter for compute_single_likelihood that.
    maxnodes : int
        The maximum amount of nodes that the grammar can have
    args : list
        The arguments to the function.
    proposal_function
        Function that tells the program how to transition from one tree to another
        (by default, it uses the RegenerationProposal function)

    Attributes
    ----------
    grammar_vector : np.ndarray
        This is a vector of
    prior_vector : np.ndarray

    """
    def __init__(self, grammar, value=None, f=None, start=None, ALPHA=0.9, maxnodes=25, args=['x'],
                 proposal_function=None, **kwargs):
        self.grammar = grammar
        self.f = f
        self.ALPHA = ALPHA
        self.maxnodes = maxnodes

        # Save all of our keywords (though we don't need v)
        self.__dict__.update(locals())

        # If this is not specified, defaultly use grammar
        if start is None:
            self.start = grammar.start
        if value is None:
            value = grammar.generate(self.start)

        FunctionHypothesis.__init__(self, value=value, f=f, args=args, **kwargs)
        # Save a proposal function
        # TODO: How to handle this in copying?
        if proposal_function is None:
            self.proposal_function = RegenerationProposal(self.grammar)

        self.likelihood = 0.0
        self.compute_grammar_vector()
        self.compute_prior_vector()

    def __call__(self, *args):
        # NOTE: This no longer catches all exceptions.
        try:
            return FunctionHypothesis.__call__(self, *args)
        except TypeError as e:
            print "TypeError in function call: ", e, str(self), "  ;  ", type(self)
            raise TypeError
        except NameError as e:
            print "NameError in function call: ", e, str(self)
            raise NameError

    def type(self):
        return self.value.type()

    def set_proposal_function(self, f):
        """Just a setter to create the proposal function."""
        self.proposal_function = f

    def compile_function(self):
        """Called in set_value to compile into a function."""
        if self.value.count_nodes() > self.maxnodes:
            return (lambda *args: raise_exception(TooBigException) )
        else:
            try:
                return evaluate_expression(str(self))
            except Exception as e:
                print "# Warning: failed to execute evaluate_expression on " + str(self)
                print "# ", e
                return lambda *args: raise_exception(EvaluationException)

    def __copy__(self, copy_value=True):
        """Make a deepcopy of everything except grammar (which is the, presumably, static grammar)."""
        # Since this is inherited, call the constructor on everything, copying what should be copied
        thecopy = type(self)(self.grammar, value=copy(self.value) if copy_value else self.value, f=self.f, proposal_function=self.proposal_function)

        # And then then copy the rest
        for k in self.__dict__.keys():
            if k not in ['self', 'grammar', 'value', 'proposal_function', 'f']:
                thecopy.__dict__[k] = copy(self.__dict__[k])

        return thecopy

    def propose(self, **kwargs):
        """
        Computes a very similar derivation from the current derivation, using the proposal function we specified
        as an option when we created an instance of LOTHypothesis
        """
        ret = self.proposal_function(self, **kwargs)
        ret[0].posterior_score = "<must compute posterior!>" # Catch use of proposal.posterior_score, without posteriors!
        return ret

    def compute_prior(self, recompute=False, vectorized=False):
        """Compute the log of the prior probability.

        Arguments
        ---------
        recompute : LOTlib.grammar
            If this is a grammar, then we use it to recompute generation probabilities for the sub-nodes
            in `self.value`. If True, we use `self.grammar`. If left as None, nothing happens.
        vectorized : LOTlib.grammar
            If this is a grammar, we compute vectorized prior.

        """
        # Point to vectorized version
        if vectorized:
            return self.compute_prior_vectorized()

        # Re-compute the FunctionNode `self.value` generation probabilities
        if recompute:
            self.value.recompute_generation_probabilities(self.grammar)

        # Compute this hypothesis prior
        if self.value.count_subnodes() > self.maxnodes:
            self.prior = -Infinity
        else:
            # Compute prior with either RR or not.
            self.prior = self.value.log_probability() / self.prior_temperature

        self.update_posterior()
        return self.prior

    def compute_prior_vectorized(self):
        """Compute `self.prior` using `self.prior_vector`."""
        prior = sum(self.prior_vector * self.grammar_vector)
        self.prior = prior
        return prior

    def compute_grammar_vector(self):
        rules = [r for sublist in self.grammar.rules.values() for r in sublist]
        self.grammar_vector = np.log([r.p for r in rules])

    def compute_prior_vector(self):
        """
        Compute `self.prior_vector` by collecting counts of each rule used to generate `self.value`.

        TODO
        ----
        BV rules in vector - do we add these as an extra item to count? or what do we do here..?

        """
        rules = [r for sublist in self.grammar.rules.values() for r in sublist]
        self.prior_vector = [0] * len(rules)

        # Use vector to collect the counts for each GrammarRule used to generate the FunctionNode
        # TODO: will `grammar_rules` include self.value??
        grammar_rules = [fn.rule for fn in self.value.subnodes()]
        for rule in grammar_rules:
            if isinstance(rule, BVUseGrammarRule):
                pass    # rule_idx = [GET index of rule with same nt as rule]
            else:
                rule_idx = rules.index(rule)
                self.prior_vector[rule_idx] += 1

    # Def compute_likelihood(self, data): # called in FunctionHypothesis.compute_likelihood
    def compute_single_likelihood(self, datum):
        """Computes the likelihood of the data

        The data here is from LOTlib.Data and is of the type FunctionData
        This assumes binary function data -- maybe it should be a BernoulliLOTHypothesis

        """
        assert isinstance(datum, FunctionData)
        return log(self.ALPHA * (self(*datum.input) == datum.output)
                   + (1.0-self.ALPHA) / 2.0)
