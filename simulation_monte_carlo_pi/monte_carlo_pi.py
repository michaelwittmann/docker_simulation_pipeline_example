import random
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import time
import sys
import getopt


class MonteCarloPi():

    def __init__(self, iterations: int = 10000, random_seed: int = None, output_dir:Path = 'output') -> None:
        self.random_seed = random_seed
        self.iterations = iterations
        self.points_inside = []
        self.points_outside = []
        self.pi_estimate = None
        self.output_dir = output_dir

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)


    def _f_circle(self, x, radius=1.0):
        y = np.sqrt(radius ** 2 - x ** 2)
        return y

    def estimate_pi(self) -> float:
        self.points_inside = []
        self.points_outside = []
        random.seed(self.random_seed)

        for i in range(0, self.iterations):
            point = (random.random(), random.random())
            if (math.sqrt(point[0] ** 2 + point[1] ** 2)) < 1.0:
                self.points_inside.append(point)
            else:
                self.points_outside.append(point)

        self.pi_estimate = (float(len(self.points_inside)) / float(self.iterations)) * 4.0
        return self.pi_estimate

    def plot(self, path=None):
        x_circle = np.linspace(0, 1, 200)
        fig, ax = plt.subplots(1, 1, figsize=(5, 5), dpi=300)
        ax.scatter(*zip(*self.points_outside[:10000]), color='r', alpha=0.5,
                   label=f'Points outside: $n={len(self.points_outside)}$')
        ax.scatter(*zip(*self.points_inside[:10000]), color='b', alpha=0.5,
                   label=f'Points inside: $n={len(self.points_inside)}$')
        ax.plot(x_circle, self._f_circle(x_circle), color='black', linestyle='--', linewidth=2, label='circle')
        ax.set_title(f'Estimate of $\pi={self.pi_estimate:.10f}$\nIterations $n={self.iterations}$')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.legend(loc='lower right')

        figure_path = self.output_dir.joinpath(f'pi_estmimate_n{self.iterations}_at{time.time_ns()}.png')
        plt.savefig(figure_path, dpi=300)


def main(argv):
    output_folder:Path = Path('results')
    iterations: int = 100000
    random_seed:int = 1

    try:
        opts, args = getopt.getopt(argv, 'ho:i:r:',['output_dir=', '--iterations', '--random_seed'])
    except getopt.GetoptError:
        print('monte_carlo_pi.py - o <output_folder>')
        sys.exit(2)


    for opt, arg in opts:
        if opt == '-h':
            print('monte_carlo_pi.py - o <output_folder>')

        if opt in ('-o', '--output_dir'):
            output_folder = Path(arg)

        if opt in ('-i', '--iterations'):
            iterations = int(arg)

        if opt in ('-r', '--random_seed'):
            random_seed = int(arg)


    print('Starting Simulation')
    simulation = MonteCarloPi(iterations=iterations, random_seed=random_seed, output_dir = output_folder)
    simulation.estimate_pi()
    simulation.plot()


if __name__ == '__main__':
    main(sys.argv[1:])
