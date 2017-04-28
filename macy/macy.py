'''
Python implementation of Flache & Macy's "caveman" model of polarization.


Flache, A., & Macy, M. W. (2011).  Small Worlds and Cultural Polarization.
The Journal of Mathematical Sociology, 35(1–3), 146–176.
http://doi.org/10.1080/0022250X.2010.532261
'''

import numpy as np
import networkx as nx

from random import choice as random_choice
from random import shuffle


def experiment(n_caves, n_agents, conn_prob=.003, iterations=1000):

    network = Network(caves(n_caves, n_agents))
    network.add_random_connections(conn_prob=conn_prob)

    for _ in range(iterations):
        network.iterate()

    return network


def caves(n_caves=20, n_agents=5):
    '''
    Make a totally connected cave with n_agents
    '''
    return nx.relabel_nodes(
        nx.caveman_graph(n_caves, n_agents),
        {i: Agent() for i in range(n_caves * n_agents)}
    )


class Network(nx.Graph):

    def __init__(self, initial_graph=None, close_connections=False):
        '''
        Create a network of any initial configuration. Provides methods
        for iterating (updating opinions and weights) and for randomizing
        connections. We can provide other helper functions or class methods
        for building specific initial configurations.

        '''
        self.graph = initial_graph

        # all pairs of vertices
        nodes = self.graph.nodes()
        n_nodes = len(nodes)
        self.possible_edges = [
            (nodes[i], nodes[j])
            for i in range(n_nodes)
            for j in range(i, n_nodes)
            if i != j
        ]

        # all pairs of vertices with current neighbors removed
        current_edges = self.graph.edges()
        self.non_neighbors = [
            el for el in self.possible_edges
            if (
                (el[0], el[1]) not in current_edges and
                (el[1], el[0]) not in current_edges
            )
        ]

    def add_random_connections(self, conn_prob):

        for pair in self.non_neighbors:
            if np.random.uniform() < conn_prob:
                self.graph.add_edge(*pair)
                self.non_neighbors.remove(pair)

    def add_random_connection(self):

        if len(self.non_neighbors) > 0:
            new_edge = random_choice(self.non_neighbors)
            self.graph.add_edge(*new_edge)

            # new_edge now defines neighbors
            self.non_neighbors.remove(new_edge)
        else:
            raise RuntimeError('No non-neighbors left to connect')

    def iterate(self):

        # asynchronous updating
        nodes = self.graph.nodes()
        shuffle(nodes)

        for agent in nodes:
            neighbors = self.graph.neighbors(agent)
            agent.opinions = opinion_update_vec(agent, neighbors)

    def draw(self):
        nx.draw_circular(self.graph)


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

    diff = abs(o2 - o1)
    numerator = np.sum(diff)

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

    ret = np.zeros(raw_update_vec.shape)
    for i, op in enumerate(agent.opinions):
        if op > 0:
            ret[i] = op + (raw_update_vec[i]*(1 - op))
        else:
            ret[i] = op + (raw_update_vec[i]*(1 + op))

    return ret


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

    d_expected = distances.sum() / (L*(L-1))

    d_sub_mean = (distances - d_expected)
    for i in range(L):
        d_sub_mean[i, i] = 0.0

    d_sub_mean_sq = np.sum(np.power(d_sub_mean, 2))

    return (1/(L*(L-1))) * d_sub_mean_sq


def distance(agent_1, agent_2):

    n_ops = len(agent_1.opinions)
    return (1.0 / n_ops) * np.sum(np.abs(agent_1.opinions - agent_2.opinions))
