from pathlib import Path
from unittest import TestCase
import math
from simulation_monte_carlo_pi.monte_carlo_pi import MonteCarloPi

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

