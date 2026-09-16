# clustering

## Goal

Our goal is to implement a clustering algorithm from scratch. Given a list of _x y_ points find _k_ stable clusters.

The input will be standard python types, but you may use numpy for the internal implementation if you want.

The output should be a list of centroids and their associated points.

```python
def cluster(points: Iterable[Point], k: int, max_iter: int = 100) -> Iterable[tuple[Centroid, list[Point]]]: ...
```

### constraints

- `stdlib` and `numpy` okay; `sklearn.cluster` and `scipy.cluster` nokay.
- It should run and output results

### tips

- get a naïve version working first and improve from there!
- provided is a `dataviz` module to prety print sets of points via the `show` function
  - `show(clusters, centroids)`
  - or `show({centroid: cluster, ...})`
- `from math import dist` and `from statistics import mean` might be useful to look at

## Description of k-mean clustering

You can implement your favorite clusering algorithim, here is a popular one called k-means!

1. _*k* initial "centroids" (in this case *k*=3) are randomly generated within the data domain (shown in color)._
   ![](https://upload.wikimedia.org/wikipedia/commons/5/5e/K_Means_Example_Step_1.svg)

2. _*k* clusters are created by associating every observation with the nearest centroid._
   ![](https://upload.wikimedia.org/wikipedia/commons/a/a5/K_Means_Example_Step_2.svg)

3. _The centroid of each of the *k* clusters becomes the new centroid._
   ![](https://upload.wikimedia.org/wikipedia/commons/3/3e/K_Means_Example_Step_3.svg)

4. _Steps 2 and 3 are repeated until convergence has been reached._
   ![](https://upload.wikimedia.org/wikipedia/commons/d/d2/K_Means_Example_Step_4.svg)

---

| Animated !                                                                       |
| -------------------------------------------------------------------------------- |
| ![](https://upload.wikimedia.org/wikipedia/commons/e/ea/K-means_convergence.gif) |
