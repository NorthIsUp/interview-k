# clustering for fun

clustering is a data analysis technique aimed at partitioning a set of objects into groups such that objects within the same group (called a cluster) exhibit greater similarity to one another than to those in other groups. There are many many many clustering algorithims out there, we want to focus on one of the simplest, _k-means_, and for determining similarity our metric is _distance_.

| _example of some points clustered by distance to each other_                                         |
| ---------------------------------------------------------------------------------------------------- |
| ![](https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c8/Cluster-2.svg/3840px-Cluster-2.svg.png) |

## Goal

Our goal is to implement a clustering algorithm from scratch. Given a list of points find `k` stable clusters.

**Input**: The input will be a sequence of `(x, y)` points (multiple datasets are available in `data.json`)
**Output**: A list of the clusters as pairs of `Centroid` and their associated `Points`.

```python
def cluster(points: Sequence[Point], k: int = 3, max_iter: int = 20) -> Sequence[tuple[Centroid, list[Point]]]:
  return []
```

### constraints

- `stlib` always ok
- if using python `numpy` okay; `sklearn.cluster` and `scipy.cluster` nokay
- if using typescript `lodash` is provided
- It should run and output results
- It should use `show` from `dataviz` to pretty print the results
- A stub function has been given to you, but you don't _have_ to use it but your solution must support the same arguments and return type somewhere.

### tips

- get a naïve version working first and improve from there!
- provided is a `dataviz` module to prety print sets of points via the `show` function. It's input is highly flexible and will attempt to "just do the right thing"
  - `show(clusters, centroids)`
  - or `show({centroid: cluster, ...})`
- `from math import dist` and `from statistics import mean` might be useful to look at
- use correct typing whenever possible, `Any` types are for kids!

## Description of k-mean clustering

You can implement your favorite clusering algorithim, here is a popular one called k-means!

| 1. _k initial "centroids" (in this case k=3) are randomly generated (shown as circles)._ |
| :--------------------------------------------------------------------------------------: |
|   ![](https://upload.wikimedia.org/wikipedia/commons/5/5e/K_Means_Example_Step_1.svg)    |

|  2. _k clusters are created by associating every point with the nearest centroid._  |
| :---------------------------------------------------------------------------------: |
| ![](https://upload.wikimedia.org/wikipedia/commons/a/a5/K_Means_Example_Step_2.svg) |

| 3. _The centroid of each of the k clusters becomes the new centroid for that cluster._ |
| :------------------------------------------------------------------------------------: |
|  ![](https://upload.wikimedia.org/wikipedia/commons/3/3e/K_Means_Example_Step_3.svg)   |

|         4. _Steps 2 and 3 are repeated until convergence has been reached._         |
| :---------------------------------------------------------------------------------: |
| ![](https://upload.wikimedia.org/wikipedia/commons/d/d2/K_Means_Example_Step_4.svg) |

---

| Animated !                                                                       |
| -------------------------------------------------------------------------------- |
| ![](https://upload.wikimedia.org/wikipedia/commons/e/ea/K-means_convergence.gif) |
