import h5py
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import seaborn as sns
import warnings

from glob import glob

from macy import Experiment


def _all_final_polarizations(hdf, experiment='random any-range'):
    return hdf[experiment + '/polarization'][:, -1]


def _final_mean(hdf, experiment='random any-range'):

    # Extract the final polarization measurement from all n_trials trials.
    all_final_polarizations = _all_final_polarizations(hdf, experiment)

    return all_final_polarizations.mean()


def _hdf_list(data_dir):
    return [h5py.File(f, 'r') for f in glob(os.path.join(data_dir, '*'))]


def _lookup_hdf(data_dir, **criteria):
    '''
    Assumes there is only one with the key, returns the first HDF file found
    in data_dir that matches the criteria.

    Arguments:
        data_dir (str): directory containing HDF files from a full modeling run
    '''
    for f in glob(os.path.join(data_dir, '*')):

        hdf = h5py.File(f, 'r')
        match = True

        for k, v in criteria.items():
            try:
                match &= hdf.attrs[k] == v
            except KeyError:
                warnings.warn('key {} not found for file {} in {}'.format(
                    k, f, data_dir
                ))
                return None

        if match:
            return hdf
        else:
            hdf.close()


def plot_p_v_noise_and_k(data_dir, Ks=[2, 3, 4, 5], save_path=None, **kwargs):

    hdfs = [h5py.File(f, 'r') for f in glob(os.path.join(data_dir, '*'))]

    # hdf0 = hdfs[0]

    # if 'distance_metric' in hdf0.attrs:
    #     distance_metric = hdf0.attrs['distance_metric']

    for K in Ks:

        if 'figsize' in kwargs:
            plt.figure(figsize=kwargs['figsize'])
        else:
            plt.figure()

        # Limit hdfs of interest to those of the K of current interest.
        final_means = [
            _final_mean(hdf) for hdf in hdfs
            if hdf.attrs['K'] == K
        ]

        # Use noise_level and S as index to force uniqueness.
        index = [
            (hdf.attrs['noise_level'], hdf.attrs['S']) for hdf in hdfs
            if hdf.attrs['K'] == K
        ]
        index = pd.MultiIndex.from_tuples(index)
        index.set_names(['noise level', 'S'], inplace=True)

        df = pd.DataFrame(
            index=index, data=final_means, columns=['Average polarization']
        ).reset_index(
        ).pivot('noise level', 'S', 'Average polarization')

        ax = sns.heatmap(df, cmap='YlGnBu_r')

        # Make noise level run from small to large.
        ax.invert_yaxis()

        ax.set_title(r'$K={}$'.format(K))

        # Force the heatmap to be square.
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        ax.set_aspect((x1 - x0)/(y1 - y0))

        if save_path is not None:
            plt.savefig(save_path + '_K={}.pdf'.format(K))
            plt.close()

    for hdf in hdfs:
        hdf.close()


def _hdfs_dict(hdfs_dir, key):
    '''
    HDFs from different runs are being saved with a UUID-based filename instead
    of some sort of identifying filename. Then the parameters are read through
    HDF attributes. This will use the relevant parameter or parameters to
    build a dictionary for keyed access to particular HDF files.

    Arguments:
        hdfs_dir (str): location of HDF files
        key (str): attribute name to use as key

    Example:
        >>> hdfs_dict = _hdfs_dict('path/to/data', 'K')
        >>> three_feature_hdf = hdfs_dict[3]  # get experiment with K=3
    '''
    hdfs_filelist = glob(os.path.join(hdfs_dir, '*'))
    hdfs = [h5py.File(f, 'r') for f in hdfs_filelist]
    return {
        hdf.attrs[key]: hdf for hdf in hdfs
    }


def _nonzero_final_polarization_selector(hdf,
                                         experiment='random any-range',
                                         tol=1e-6):
    final_polarizations = _all_final_polarizations(hdf, experiment=experiment)
    return final_polarizations > tol


def final_polarization_histogram(data_dir, **criteria):

    polarizations = _all_final_polarizations(
        _lookup_hdf(data_dir, **criteria)
    )
    plt.hist(polarizations)


def plot_S_K_experiment(data_dirs, plot_start=0, agg_fun=np.mean,
                        save_path=None, lim_xticks=False, **kwargs):
    '''
    Plot average, median, or other aggregate of final polarizaiton over
    trials for various values of initial opinion magnitude S and cultural
    complexity K. Pass optional kwargs of figsize or other matplotlib
    plot options.

    Arguments:
        data_dirs (str or list): Location of HDF files to be used
        agg_fun (function): Method for aggregating final polarizations
        plot_start (int): Index to start plotting at. Used for excluding
        uninteresting parts of the plot.
    Returns:
        None
    '''
    if 'figsize' in kwargs:
        plt.figure(figsize=kwargs['figsize'])
        del kwargs['figsize']
    else:
        plt.figure()

    hdf_lookup = 'random any-range/polarization'

    if type(data_dirs) is str:
        data_dirs = [data_dirs]

    # Build list of HDF files from data directories.
    hdfs = []
    for d in data_dirs:
        hdfs += [h5py.File(f) for f in glob(os.path.join(d, '*.hdf5'))]

    Ks = list(set(hdf.attrs['K'] for hdf in hdfs))
    Ks.sort()

    n_hdfs_max = 0.0
    for K in Ks:

        if 'noise_level' in hdfs[0].attrs:
            hdfs_K = [hdf for hdf in hdfs
                      if hdf.attrs['K'] == K
                      and hdf.attrs['noise_level'] == 0.0]
        else:
            hdfs_K = [hdf for hdf in hdfs if hdf.attrs['K'] == K]

        hdfs_K.sort(key=lambda x: x.attrs['S'])

        n_hdfs_K = len(hdfs_K)
        y_vals = np.zeros(n_hdfs_K)
        y_std = np.zeros(n_hdfs_K)

        for idx in range(n_hdfs_K):
            # Get final polarization value for all trials and average.
            final_polarizations = hdfs_K[idx][hdf_lookup][:, -1]
            y_vals[idx] = agg_fun(final_polarizations)
            y_std[idx] = final_polarizations.std()

        x = [str(hdf.attrs['S']) for hdf in hdfs_K]
        if n_hdfs_max < n_hdfs_K:
            xmax = x
            n_hdfs_max = n_hdfs_K

        # These [3:] are ugly, but just working for the data.
        # plt.plot(x[3:], y_vals[3:], 'o-', label=r'$K={}$'.format(K),
        #          lw=2, ms=8, alpha=0.65)
        plt.plot(x[plot_start:], y_vals[plot_start:], 'o-',
                 label=r'$K={}$'.format(K), lw=2, ms=8, alpha=0.65)

    plt.legend(loc='upper left')
    if agg_fun == np.mean:
        plt.ylabel('Average polarization')
    elif agg_fun == np.median:
        plt.ylabel('Median polarization')
    plt.xlabel('S')

    if plot_start > 0:
        plt.xticks(range(n_hdfs_K)[:-plot_start], x[plot_start:])
    if lim_xticks:
        plt.xticks(range(n_hdfs_max)[::2], xmax[::2])

    if save_path:
        plt.savefig(save_path)


MPL_COLORS = plt.rcParams['axes.prop_cycle'].by_key()['color']


def plot_single_S_K(data_dir, K, save_path=None, semilogy=False, **kwargs):

    if 'figsize' in kwargs:
        plt.figure(figsize=kwargs['figsize'])
        del kwargs['figsize']
    else:
        plt.figure()

    hdfs = _hdf_list(data_dir)
    hdfs_K = [hdf for hdf in hdfs if hdf.attrs['K'] == K]
    hdfs_K.sort(key=lambda x: x.attrs['S'])
    hdf0 = hdfs_K[0]

    n_trials = len(_all_final_polarizations(hdf0))
    S_vals = [hdf.attrs['S'] for hdf in hdfs_K]

    if semilogy:
        plot_fun = plt.semilogy
    else:
        plot_fun = plt.plot

    # Get color to match the plot of averages for all K.
    # Subtract 2 because first K plot is K=2. See
    # https://stackoverflow.com/questions/42086276/get-default-line-colour-cycle
    if K > 1:
        color = MPL_COLORS[K - 2]
    elif K == 1:
        color = 'black'

    # Plot all final pol values for every S value. One HDF for each S.
    for idx, hdf in enumerate(hdfs_K):
        # Plot with a legend on the first S value.
        if idx == 0:
            plot_fun([S_vals[idx]]*n_trials, _all_final_polarizations(hdf),
                     's', color=color, ms=8, alpha=0.25,
                     label='Trial result', **kwargs)
        else:
            plot_fun([S_vals[idx]]*n_trials, _all_final_polarizations(hdf),
                     's', color=color, ms=8, alpha=0.25, **kwargs)

    means = [_final_mean(hdf) for hdf in hdfs_K]

    if 'lw' not in kwargs:
        kwargs['lw'] = 2

    plot_fun(S_vals, means, color=color, marker=None,
             label='Average', **kwargs)

    plt.ylabel('Polarization')
    plt.xlabel('S')
    plt.legend()
    plt.title(r'$K={}$'.format(K))

    if save_path:
        plt.savefig(save_path)


def plot_single_K_experiment(data_dir, experiment, x=[1, 2, 3, 5, 10],
                             save_path=None, semilogy=False, **kwargs):

    if 'figsize' in kwargs:
        plt.figure(figsize=kwargs['figsize'])
        del kwargs['figsize']
    else:
        plt.figure()

    hdfs = _hdf_list(data_dir)

    color = {
        'connected caveman': 'r',
        'random short-range': 'b',
        'random any-range': 'g'
    }[experiment]

    hdfs.sort(key=lambda x: x.attrs['K'])
    hdfs_lim = [hdf for hdf in hdfs if hdf.attrs['K'] in x]

    final_polarizations_cc = [
        _all_final_polarizations(hdf, experiment=experiment)
        for hdf in hdfs_lim
    ]

    n_trials = len(final_polarizations_cc[0])

    for x_idx, K in enumerate(x):
        if x_idx == 0:
            plt.plot([x_idx]*n_trials, final_polarizations_cc[x_idx],
                     marker='s', ms=8, alpha=0.25, lw=0,
                     color=color, label='Trial result')
        else:
            plt.plot([x_idx]*n_trials, final_polarizations_cc[x_idx],
                     marker='s', ms=8, alpha=0.25, lw=0,
                     color=color)

    means = [_final_mean(hdf, experiment=experiment)
             for hdf in hdfs_lim]

    plt.plot(means, color=color, marker=None, label='Average')

    plt.xticks(range(len(x)), [str(el) for el in x])
    plt.legend(loc='best')
    plt.xlabel('K')
    plt.ylabel('Polarization')
    plt.title('Average and trial polarization for {}'.format(experiment))

    if save_path:
        plt.savefig(save_path)


def plot_figure12b(data_dir, stddev=True, full_ylim=True, x=None,
                   save_path=None, **kwargs):
    '''
    This figure plots average final polarization against K, the number of
    opinion features.
    '''
    if 'figsize' in kwargs:
        plt.figure(figsize=kwargs['figsize'])
    else:
        plt.figure()

    colors = ['r', 'b', 'g']

    if x is None:
        x = [1, 2, 3, 5, 10]
    xlen = len(x)

    hdf_dict = _hdfs_dict(data_dir, 'K')

    keys = ['connected caveman', 'random short-range', 'random any-range']
    for key_idx, key in enumerate(keys):

        y_vals = np.zeros(xlen)
        y_std = np.zeros(xlen)
        yerr_low = np.zeros(xlen)
        yerr_high = np.zeros(xlen)

        for x_idx, K in enumerate(x):

            hdf = hdf_dict[K]

            final_polarizations = hdf[key + '/polarization'][:, -1]

            p_low = np.percentile(final_polarizations, 25)
            p_high = np.percentile(final_polarizations, 75)
            p_mean = np.mean(final_polarizations)

            yerr_low[x_idx] = p_mean - p_low
            yerr_high[x_idx] = p_high - p_mean
            y_vals[x_idx] = p_mean
            y_std[x_idx] = np.std(final_polarizations)

        yerr = np.vstack([yerr_low, yerr_high])

        if stddev is True:
            plt.errorbar(range(len(x)), y_vals, yerr=y_std,
                         marker='o', ms=8,
                         color=colors[key_idx], label=key, capsize=5,
                         alpha=0.65)
        elif stddev == 'off':
            plt.plot(range(len(x)), y_vals, marker='o', ms=8,
                     color=colors[key_idx], label=key,
                     alpha=0.65)
        else:
            plt.errorbar(range(len(x)), y_vals, yerr=yerr, marker='o', ms=8,
                         color=colors[key_idx], label=key, capsize=5,
                         alpha=0.65)

    plt.xticks(range(len(x)), [str(el) for el in x])
    plt.legend(loc='best')
    plt.xlabel('K')
    plt.ylabel('Polarization')

    if full_ylim:
        plt.axhline(y=.25, color='grey', ls='--', lw=1)
        plt.axhline(y=.5, color='grey', ls='--', lw=1)
        plt.axhline(y=.75, color='grey', ls='--', lw=1)
        plt.yticks([0.0, 0.25, 0.5, 0.75, 1.0])
        # plt.ylim(0, 1)

    if save_path:
        plt.savefig(save_path)


class ExperimentRerun(Experiment):

    def __init__(self, initial_opinions, metadata=None,
                 experiment='connected caveman', n_iter_sync=1000):
        '''
        Initialize a fresh experiment using the information in the HDF.

        Arguments:
            hdf (h5py.File): TODO
            trial_idx (int): Index of the trial to re-run.
        '''
        # meta = hdf.attrs
        # self.K = meta['K']

        # TODO add support for re-running IC and noise experiments.
        # if 'S' in meta:
        #     pass
        # if 'noise_level' in meta:
        #     pass

        # For now only doing these re-runs with n_per_cave=5 and n_caves=20.
        n_per_cave = 5
        n_caves = 20

        # data = hdf[experiment]

        # initial_opinions = data['coords'][trial_idx, 0]

        Experiment.__init__(self, n_caves, n_per_cave, n_iter_sync=n_iter_sync,
                            distance_metric='fm2011')

        self.n_iter_sync = n_iter_sync
        for idx, agent in enumerate(self.network.graph.nodes()):
            agent.opinions = initial_opinions[idx]

        self.history['coords'].append(
            [n.opinions for n in self.network.graph.nodes()]
        )


def plot_single_noise_param(data_dir, K, save_path=None, **kwargs):

    all_hdfs = _hdf_list(data_dir)
    hdfs_K = [hdf for hdf in all_hdfs if hdf.attrs['K'] == K]

    if 'S' in kwargs:
        S = kwargs['S']
        del kwargs['S']
        hdfs = [hdf for hdf in hdfs_K if hdf.attrs['S'] == S]
        title = r'$K={}$ and $S={}$'.format(K, S)
        xlabel = 'Noise level'
        x_key = 'noise_level'

    elif 'noise_level' in kwargs:

        noise_level = kwargs['noise_level']
        del kwargs['noise_level']

        hdfs = [hdf for hdf in hdfs_K
                if hdf.attrs['noise_level'] == noise_level]

        title = r'$K={}$ and noise level $={}$'.format(K, noise_level)
        xlabel = 'Maximum initial opinion magnitude'
        x_key = 'S'

    else:
        for hdf in all_hdfs:
            hdf.close()
        raise RuntimeError('Either S or noise_level kwarg must be given')

    hdfs.sort(key=lambda x: x.attrs[x_key])

    x_vals = [hdf.attrs[x_key] for hdf in hdfs]
    n_trials = len(_all_final_polarizations(hdfs[0]))

    # Still going to code data points by color according to K value.
    if K > 1:
        color = MPL_COLORS[K - 2]

    for idx, hdf in enumerate(hdfs):
        if idx == 0:
            plt.plot([x_vals[idx]]*n_trials, _all_final_polarizations(hdf),
                     marker='s', color=color, ms=8, alpha=0.25, lw=0,
                     label='Trial result', **kwargs)
        else:
            plt.plot([x_vals[idx]]*n_trials, _all_final_polarizations(hdf),
                     marker='s', color=color, ms=8, alpha=0.25, lw=0, **kwargs)

    means = [_final_mean(hdf) for hdf in hdfs]

    if 'lw' not in kwargs:
        kwargs['lw'] = 2

    plt.plot(x_vals, means, color=color, marker=None,
             label='Average', **kwargs)

    plt.ylabel('Polarization')
    plt.xlabel(xlabel)
    plt.title(title)
    plt.legend()

    if save_path is not None:
        plt.savefig(save_path)

    for hdf in all_hdfs:
        hdf.close()