#!/usr/bin/env python
"""Example Test cases for monte_carlo_pi

They are mainly used to show the integration of test-cases in a gitHub CI/CD pipeline.
"""

from pathlib import Path
from unittest import TestCase
import math
from example_monte_carlo_pi.monte_carlo_pi import MonteCarloPi


__author__ = "Michael Wittmann "
__copyright__ = "Copyright 2020, Michael Wittmann"

__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Michael Wittmann"
__email__ = "michael.wittmann@tum.de"
__status__ = "Example"

class TestMonteCarloPi(TestCase):


    def test_estimate_pi(self):
        simulation = MonteCarloPi(iterations=100000, random_seed=12345, output_dir=Path('ouput'))
        pi_hat = simulation.estimate_pi()
        print(abs(pi_hat/math.pi -1) )
        self.assertTrue(abs(pi_hat/math.pi -1) < 0.001)


    def test_plot(self):
        simulation = MonteCarloPi(iterations=100000, random_seed=12345, output_dir=Path('ouput'))
        simulation.estimate_pi()
        simulation.plot()

