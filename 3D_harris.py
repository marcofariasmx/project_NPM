# -*- coding: utf-8 -*-
"""
Created on Sun Feb 17 15:27:42 2019
@author: juliette rengot

A robust 3D IPD based on harris detector
"""
import itertools
import scipy
import numpy as np
from sklearn.decomposition import PCA
from math import sqrt
import time

#import sys
#sys.path.append("C://Users//juliette//Desktop//enpc//3A//S2//Nuage_de_points_et_modélisation_3D//projet//github//utils")
#from ply import write_ply, read_ply
from utils.ply import write_ply, read_ply

import warnings
warnings.filterwarnings("ignore")

import neighborhoods
import transformation



def dot_product(vector_1, vector_2):
  return sum((a*b) for a, b in zip(vector_1, vector_2))
def length(vector):
  return sqrt(dot_product(vector, vector))
def angle(v1, v2):
    a = dot_product(v1, v2)/(length(v1)*length(v2))
    a = np.clip(a, -1, 1)
    return(np.arccos(a))

def polyfit3d(x, y, z, order=3):
    ncols = (order + 1)**2
    G = np.zeros((x.size, ncols))
    ij = itertools.product(range(order+1), range(order+1))
    for k, (i,j) in enumerate(ij):
        G[:,k] = x**i * y**j
    m, _, _, _ = np.linalg.lstsq(G, z)
    return m



if __name__ == '__main__':
    print("Program execution began...")
    #parameters
    plot = False
    n_neighbours = 3
    delta = 0.025
    k = 0.04
    fraction = 0.1
    cluster_threshold = 0.01
    scale_range = [0.5, 2.0]
    offset_range = [10**(-4), 10**(-3)]
    
    #Begin counting time
    start_time = time.time()

    # Load point cloud
    #file_path = 'data//building-bin-2-halfsize.ply' # Path of the file
    file_path = 'data//airplane.ply' # Path of the file
    data = read_ply(file_path)
    points = np.vstack((data['x'], data['y'], data['z'])).T
    print("Point cloud loaded")
                       
    #initialisation of the solution
    labels_fraction = np.zeros(len(points))
    labels_cluster = np.zeros(len(points))
    resp = np.zeros(len(points))
    
    #compute neighborhood
    neighborhood = neighborhoods.brute_force_KNN(points, n_neighbours)
#    neighborhood = neighborhoords.brute_force_spherical(points, n_neighbours)
#    neighborhood = neighborhoords.k_ring_delaunay(points, n_neighbours)
#    neighborhood = neighborhoords.k_ring_delaunay_adaptive(points, delta)
    print("neighborhood algo execution complete...")

    for i in range(len(points)) :
#    for i in neighborhood.keys() :
        #neighbors = points[neighborhood[i], :]
        points_centred, _ = transformation.centering_centroid(points)
        
        #best fitting point
        pca = PCA(n_components=3) #Principal Component Analysis
        points_pca = pca.fit_transform(np.transpose(points_centred))
        eigenvalues, eigenvectors = np.linalg.eigh(points_pca)
        #idx = np.argmin(eigenvalues, axis=0)
        #best_fit_normal = eigenvectors[idx,:]
        
        """
        This next part (rotate the cloud) makes the problem become an O^2 problem, it would be
        worth to see if it can be addressed to reduce execution time
        """
        #rotate the cloud
        for j in range(points.shape[0]):
            points[j, :] = np.dot(np.transpose(eigenvectors), points[j, :])
            
        #restrict to XY plane and translate
        points_2D = points[:,:2]-points[i,:2]
        
        #fit a quadratic surface
        m = polyfit3d(points_2D[:,0], points_2D[:,1], points[:,2], order=2)
        m = m.reshape((3,3))
        
        #Compute the derivative
        fx2 =  m[1, 0]*m[1, 0] + 2*m[2, 0]*m[2, 0] + 2*m[1, 1]*m[1, 1] #A
        fy2 =  m[1, 0]*m[1, 0] + 2*m[1, 1]*m[1, 1] + 2*m[0, 2]*m[0, 2] #B
        fxfy = m[1, 0]*m[0, 1] + 2*m[2, 0]*m[1, 1] + 2*m[1, 1]*m[0, 2] #C
          
        #Compute response
        resp[i] = fx2*fy2 - fxfy*fxfy - k*(fx2 + fy2)*(fx2 + fy2);

        print("looped: ", i, "/", len(points), "  -  ", round(i/len(points)*100, 2), "%")

    print("neighborhood computed")

    #Select interest points
    #search for local maxima
    candidate = []
    for i in range(len(points)) :
    #for i in neighborhood.keys() :
        if resp[i] >= np.max(resp[neighborhood[i]]) :
            candidate.append([i, resp[i]])
    #sort by decreasing order
    candidate.sort(reverse=True, key=lambda x:x[1])
    candidate = np.array(candidate)
    
    #Method 1 : fraction
    interest_points = np.array(candidate[:int(fraction*len(points)), 0], dtype=np.int)
    labels_fraction[interest_points] = 1
    
    #Method 2 : cluster
    Q = points[int(candidate[0, 0]), :].reshape((1,-1))
    for i in range(1, len(candidate)) :
        query = points[int(candidate[i, 0]), :].reshape((1,-1))
        distances = scipy.spatial.distance.cdist(query, Q, metric='euclidean')
        if np.min(distances) > cluster_threshold :
            Q = np.concatenate((Q, query), axis=0)
            labels_cluster[int(candidate[i, 0])] = 1
          
    print("interest points selected")
    
    # Save the result
    print("Saving the result...")
    #write_ply('data//results//building-bin-2-halfsize.ply', [points, labels_fraction, labels_cluster], ['x', 'y', 'z', 'labels_fraction', 'labels_cluster'])
    write_ply('data//results//airplane-knn.ply', [points, labels_fraction, labels_cluster], ['x', 'y', 'z', 'labels_fraction', 'labels_cluster'])

    elapsed_time = time.time() - start_time

    print("Total execution time: ", elapsed_time, " seconds")