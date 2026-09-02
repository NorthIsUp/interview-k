# clustering

Our goal is to implement a clustering algorithm from scratch. Given a list of _x y_ points find _k_ stable clusters.

The input will be standard python types, but you may use numpy for the internal implementation if you want.

The output should be a list of centroids and their associated points.

```python
def cluster(
	points: Iterable[Point],
	k: int,
	max_iter: int = 100
) -> Iterable[tuple[Centroid, list[Point]]]:
	...
```

### constraints

- `stdlib` and `numpy` okay; `sklearn.cluster` and `scipy.cluster` nokay.
- It should run and output results

### tips

- get a naïve version working first and improve from there!
- provided is a `dataviz` module to prety print sets of points

```py
show(*points: tuple[int, int])                  # just show all the points as ·
show(*clusters: Iterable[tuple[int, int]])               # -> one mark per group, in argument order
show(*clusters, centroids=C)  # -> centroids overlaid as their group's digit
```

- `from math import dist` and `from statistics import mean` might be useful to look at

### Description of k-mean clustering

You can implement your favorite clusering algorithim, here is a popular one!

| 🖼️                                                                                  | 🔤                                                                                                       |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| ![](https://upload.wikimedia.org/wikipedia/commons/5/5e/K_Means_Example_Step_1.svg) | *k* initial "means" (in this case *k*=3) are randomly generated within the data domain (shown in color). |
| ![](https://upload.wikimedia.org/wikipedia/commons/a/a5/K_Means_Example_Step_2.svg) | *k* clusters are created by associating every observation with the nearest mean.                         |
| ![](https://upload.wikimedia.org/wikipedia/commons/3/3e/K_Means_Example_Step_3.svg) | The centroid of each of the _k_ clusters becomes the new mean.                                           |
| ![](https://upload.wikimedia.org/wikipedia/commons/d/d2/K_Means_Example_Step_4.svg) | Steps 2 and 3 are repeated until convergence has been reached.                                           |

| Animated !                                                                       |
| -------------------------------------------------------------------------------- |
| ![](https://upload.wikimedia.org/wikipedia/commons/e/ea/K-means_convergence.gif) |
