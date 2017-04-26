'''
Python implementation of Flache & Macy's "caveman" model of polarization.


Flache, A., & Macy, M. W. (2011).  Small Worlds and Cultural Polarization.
The Journal of Mathematical Sociology, 35(1–3), 146–176.
http://doi.org/10.1080/0022250X.2010.532261
'''

import numpy as np
import networkx as nx

from itertools import product
from random import choice as random_choice


class Cave(nx.Graph):

    def __init__(self, n_agents=5):
        '''
        Initialize a single cave with n_agents
        '''
        pass


class Network(nx.Graph):

    def __init__(self, initial_graph=None, close_connections=False):
        '''
        Create a network of any initial configuration. Provides methods
        for iterating (updating opinions and weights) and for randomizing
        connections. We can provide other helper functions or class methods
        for building specific initial configurations.

        '''
        self.graph = initial_graph

        # Next two blocks (XXX) list of edges that could be added
        # ("non_neighbors") seems convoluted, but it works for now.
        # First it gets a list of all undirected pairs of vertices in
        # the graph. Then it removes any of these pairs that are already
        # connected in the graph

        # XXX
        # all pairs of vertices
        self.possible_edges = list(
            {n1, n2} for n1, n2 in
            product(self.graph.nodes(), self.graph.nodes())
            if n1 != n2
        )

        # XXX
        # all pairs of vertices with current neighbors removed
        self.non_neighbors = list(np.unique(
            [el for el in self.possible_edges if
             el not in [{n1, n2} for n1, n2 in self.graph.edges()]]
        ))

    def add_random_connection(self):

        if len(self.non_neighbors) > 0:
            new_edge = random_choice(self.non_neighbors)
            self.graph.add_edge(*new_edge)

            # new_edge now defines neighbors
            self.non_neighbors.remove(new_edge)
        else:
            raise RuntimeError('No non-neighbors left to connect')

    def iterate(self):
        pass


class Experiment:

    def __init__(self, n_per_cave, n_caves):
        self.network = Network([Cave(n_per_cave) for _ in range(n_caves)])

    def run(self, pct_rewire):

        pass


class Agent:

    def __init__(self, n_opinions=2, opinion_fill='random'):
        self.opinions = np.random.uniform(low=-1.0, high=1.0, size=2)


def weight(a1, a2, nonnegative=False):
    '''
    Calculate connection weight between two agents (Equation [1])
    '''
    o1 = a1.opinions
    o2 = a2.opinions

    if o1.shape != o2.shape:
        raise RuntimeError("Agent's opinion vectors have different shapes")
    K = len(o1)

    numerator = np.sum(np.abs(d) for d in o1 - o2)

    if nonnegative:
        nonneg_fac = 2.0
    else:
        nonneg_fac = 1.0

    return 1 - (numerator / (nonneg_fac * K))


def raw_opinion_update_vec(agent, neighbors):

    factor = (1.0 / (2.0 * len(neighbors)))

    return factor * np.sum(
        weight(agent, neighbor) * (neighbor.opinions - agent.opinions)
        for neighbor in neighbors
    )


def opinion_update_vec(agent, neighbors):

    raw_update_vec = raw_opinion_update_vec(agent, neighbors)

    return agent.opinions + (np.multiply(1 - agent.opinions, raw_update_vec))


def polarization(network):
    '''
    Implementing Equation 3
    '''

    nodes = network.nodes()

    L = len(nodes)
    distances = np.zeros((L, L))

    for i in range(L):
        for j in range(L):
            distances[i, j] = distance(nodes[i], nodes[j])
            print('i={}, j={}, distance={}'.format(i, j, distances[i, j]))

    d_expected = distances.sum() / (L*(L-1))

    print(d_expected)

    d_sub_mean = (distances - d_expected)
    for i in range(L):
        d_sub_mean[i, i] = 0.0

    d_sub_mean_sq = np.sum(np.power(d_sub_mean, 2))

    return (1/(L*(L-1))) * d_sub_mean_sq


def distance(agent_1, agent_2):

    n_ops = len(agent_1.opinions)
    print(n_ops)
    return (1.0 / n_ops) * np.sum(np.abs(agent_1.opinions - agent_2.opinions))
