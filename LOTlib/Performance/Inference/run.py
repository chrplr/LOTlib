# -*- coding: utf-8 -*-
"""
        Simple evaluation of number schemes -- read LOTlib.Performance.Evaluation to see what the output is
"""

import LOTlib
import os
import re
from itertools import product
from LOTlib.Performance.Evaluation import load_model
from LOTlib.MPI.MPI_map import MPI_map, get_rank

from optparse import OptionParser
parser = OptionParser()
parser.add_option("--out", dest="OUT", type="string", help="Output prefix", default="output-InfereceSchemes")
parser.add_option("--samples", dest="SAMPLES", type="int", default=100000, help="Number of samples to run")
parser.add_option("--repetitions", dest="REPETITONS", type="int", default=100, help="Number of repetitions to run")
parser.add_option("--print-every", dest="PRINTEVERY", type="int", default=1000, help="Evaluation prints every this many")
parser.add_option("--models", dest="MODELS", type="str", default='SymbolicRegression.Galileo,Magnetism.Simple,RationalRules,RegularExpression,Number:100,Number:300', help="Which models do we run on?")
options, _ = parser.parse_args()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# These get defined for each process
from LOTlib.Performance.Evaluation import evaluate_sampler
from LOTlib.Inference.EnumerationInference import EnumerationInference
from LOTlib.Inference.ParallelTempering import ParallelTemperingSampler
from LOTlib.Inference.MetropolisHastings import MHSampler
from LOTlib.Inference.TabooMCMC import TabooMCMC
from LOTlib.Inference.ParticleSwarm import ParticleSwarm, ParticleSwarmPriorResample
from LOTlib.Inference.MultipleChainMCMC import MultipleChainMCMC
from LOTlib.Inference.PartitionMCMC import PartitionMCMC

def run_one(iteration, model, sampler_type):
    if LOTlib.SIG_INTERRUPTED: # do this so we don't create (big) hypotheses
        return

    data, make_h0 = load_model(model)
    h0 = make_h0()
    grammar = h0.grammar

    # Create a sampler
    if sampler_type == 'mh_sample_A':               sampler = MHSampler(h0, data, options.SAMPLES,  likelihood_temperature=1.0)
    elif sampler_type == 'mh_sample_B':             sampler = MHSampler(h0, data, options.SAMPLES,  likelihood_temperature=1.1)
    elif sampler_type == 'mh_sample_C':             sampler = MHSampler(h0, data, options.SAMPLES,  likelihood_temperature=1.25)
    elif sampler_type == 'mh_sample_D':             sampler = MHSampler(h0, data, options.SAMPLES,  likelihood_temperature=2.0 )
    elif sampler_type == 'mh_sample_E':             sampler = MHSampler(h0, data, options.SAMPLES,  likelihood_temperature=5.0 )
    elif sampler_type == 'particle_swarm_A':        sampler = ParticleSwarm(make_h0, data, steps=options.SAMPLES, within_steps=10)
    elif sampler_type == 'particle_swarm_B':        sampler = ParticleSwarm(make_h0, data, steps=options.SAMPLES, within_steps=100)
    elif sampler_type == 'particle_swarm_C':        sampler = ParticleSwarm(make_h0, data, steps=options.SAMPLES, within_steps=200)
    elif sampler_type == 'particle_swarm_prior_sample_A':        sampler = ParticleSwarmPriorResample(make_h0, data, steps=options.SAMPLES, within_steps=10)
    elif sampler_type == 'particle_swarm_prior_sample_B':        sampler = ParticleSwarmPriorResample(make_h0, data, steps=options.SAMPLES, within_steps=100)
    elif sampler_type == 'particle_swarm_prior_sample_C':        sampler = ParticleSwarmPriorResample(make_h0, data, steps=options.SAMPLES, within_steps=200)
    elif sampler_type == 'multiple_chains_A':       sampler = MultipleChainMCMC(make_h0, data, steps=options.SAMPLES, nchains=10)
    elif sampler_type == 'multiple_chains_B':       sampler = MultipleChainMCMC(make_h0, data, steps=options.SAMPLES, nchains=100)
    elif sampler_type == 'multiple_chains_C':       sampler = MultipleChainMCMC(make_h0, data, steps=options.SAMPLES, nchains=1000)
    elif sampler_type == 'parallel_tempering_A':    sampler = ParallelTemperingSampler(make_h0, data, steps=options.SAMPLES, within_steps=10, temperatures=[1.0, 1.025, 1.05], swaps=1, yield_only_t0=False)
    elif sampler_type == 'parallel_tempering_B':    sampler = ParallelTemperingSampler(make_h0, data, steps=options.SAMPLES, within_steps=10, temperatures=[1.0, 1.25, 1.5], swaps=1, yield_only_t0=False)
    elif sampler_type == 'parallel_tempering_C':    sampler = ParallelTemperingSampler(make_h0, data, steps=options.SAMPLES, within_steps=10, temperatures=[1.0, 2.0, 5.0], swaps=1, yield_only_t0=False)
    elif sampler_type == 'taboo_A':                 sampler = TabooMCMC(h0, data, steps=options.SAMPLES, skip=0, penalty= 0.001)
    elif sampler_type == 'taboo_B':                 sampler = TabooMCMC(h0, data, steps=options.SAMPLES, skip=0, penalty= 0.010)
    elif sampler_type == 'taboo_C':                 sampler = TabooMCMC(h0, data, steps=options.SAMPLES, skip=0, penalty= 0.100)
    elif sampler_type == 'taboo_D':                 sampler = TabooMCMC(h0, data, steps=options.SAMPLES, skip=0, penalty= 1.000)
    elif sampler_type == 'taboo_E':                 sampler = TabooMCMC(h0, data, steps=options.SAMPLES, skip=0, penalty=10.000)
    elif sampler_type == 'partitionMCMC_A':         sampler = PartitionMCMC(grammar, make_h0, data, 10, steps=options.SAMPLES)
    elif sampler_type == 'partitionMCMC_B':         sampler = PartitionMCMC(grammar, make_h0, data, 100, steps=options.SAMPLES)
    elif sampler_type == 'partitionMCMC_C':         sampler = PartitionMCMC(grammar, make_h0, data, 1000, steps=options.SAMPLES)
    elif sampler_type == 'enumeration_A':           sampler = EnumerationInference(grammar, make_h0, data, steps=options.SAMPLES)
    else: assert False, "Bad sampler type: %s" % sampler_type

    with open("output/out-aggregate.%s" % get_rank(), 'a') as out_aggregate:
        with open(os.devnull,'w')  as out_hypotheses:
            # Run evaluate on it, printing to the right locations
            evaluate_sampler(sampler, trace=False, prefix="\t".join(map(str, [model, iteration, sampler_type])),  out_hypotheses=out_hypotheses, out_aggregate=out_aggregate, print_every=options.PRINTEVERY)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create all parameters
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# For each process, create the lsit of parameter
params = [list(g) for g in product(range(options.REPETITONS),\
                                    re.split(r',', options.MODELS),
                                    ['multiple_chains_A', 'multiple_chains_B', 'multiple_chains_C',
                                     'taboo_A', 'taboo_B', 'taboo_C', 'taboo_D',
                                     'particle_swarm_A', 'particle_swarm_B', 'particle_swarm_C',
                                     'particle_swarm_prior_sample_A', 'particle_swarm_prior_sample_B', 'particle_swarm_prior_sample_C',
                                     'mh_sample_A', 'mh_sample_B', 'mh_sample_C', 'mh_sample_D', 'mh_sample_E',
                                     'parallel_tempering_A', 'parallel_tempering_B', 'parallel_tempering_C',
                                     'partitionMCMC_A', 'partitionMCMC_B', 'partitionMCMC_C',
                                     'enumeration_A'])]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Actually run
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MPI_map(run_one, params, random_order=False)
