#!/usr/bin/env python
# encoding: utf-8
#
# @Date: Feb 22, 2018
# @Filename: ralign.py


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import numpy as np


def umeyama(X, Y):
    """Rigid alignment of two sets of points in k-dimensional Euclidean space.

    Given two sets of points in correspondence, this function computes the
    scaling, rotation, and translation that define the transform TR that
    minimizes the sum of squared errors between TR(X) and its corresponding
    points in Y.  This routine takes O(n k^3)-time.

    Parameters:
        X:
            A ``k x n`` matrix whose columns are points.
        Y:
            A ``k x n`` matrix whose columns are points that correspond to the
            points in X

    Returns:
        c,R,t:
            The  scaling, rotation matrix, and translation vector defining the
            linear map TR as ::

                       TR(x) = c * R * x + t

             such that the average norm of ``TR(X(:, i) - Y(:, i))`` is
             minimized.

    Copyright: Carlo Nicolini, 2013

    Code adapted from the Mark Paskin Matlab version from
    http://openslam.informatik.uni-freiburg.de/data/svn/tjtf/trunk/matlab/ralign.m

    See paper by Umeyama (1991)

    """

    m, n = X.shape

    mx = X.mean(1)
    my = Y.mean(1)

    Xc = X - np.tile(mx, (n, 1)).T
    Yc = Y - np.tile(my, (n, 1)).T

    sx = np.mean(np.sum(Xc * Xc, 0))

    Sxy = np.dot(Yc, Xc.T) / n

    U, D, V = np.linalg.svd(Sxy, full_matrices=True, compute_uv=True)
    V = V.T.copy()

    r = np.linalg.matrix_rank(Sxy)
    S = np.eye(m)

    if r < (m - 1):
        raise ValueError('not enough independent measurements')

    if (np.linalg.det(Sxy) < 0):
        S[-1, -1] = -1
    elif (r == m - 1):
        if (np.linalg.det(U) * np.linalg.det(V) < 0):
            S[-1, -1] = -1

    R = np.dot(np.dot(U, S), V.T)
    c = np.trace(np.dot(np.diag(D), S)) / sx
    t = my - c * np.dot(R, mx)

    return c, R, t


if __name__ == '__main__':

    p_A = np.random.rand(3, 10)
    R_BA = np.array([[0.9689135, -0.0232753, 0.2463025],
                     [0.0236362, 0.9997195, 0.0014915],
                     [-0.2462682, 0.0043765, 0.9691918]])
    B_t_BA = np.array([[1], [2], [3]])
    p_B = np.dot(R_BA, p_A) + B_t_BA

    # Reconstruct the transformation with umeyama
    c, R_BA_hat, B_t_BA_hat = umeyama(p_A, p_B)
    print('Rotation matrix=\n', R_BA_hat)
    print('Scaling coefficient=', c)
    print('Translation vector=', B_t_BA_hat)
