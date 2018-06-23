import numpy as np
from copy import deepcopy
import unittest

from pyfiberamp.fibers import YbDopedFiber
from pyfiberamp.dynamic import DynamicSimulation
from pyfiberamp.steady_state import SteadyStateSimulation


class DynamicSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nt = 1e25
        r = 3e-6
        cls.fiber = YbDopedFiber(length=0.1, core_radius=r, core_na=0.12, ion_number_density=cls.nt)
        cls.fiber.default_signal_mode_shape_parameters['functional_form'] = 'gaussian'
        cls.fiber.default_pump_mode_shape_parameters['functional_form'] = 'gaussian'
        cls.pump_power = 0.5
        cls.signal_power = 0.1
        cls.signal_wl = 1040e-9
        cls.pump_wl = 980e-9
        cls.time_steps = 50000
        cls.z_nodes = 150
        cls.steady_state_dt = 1e-5

    def test_steady_state_python_and_cpp_single_ring(self):
        steady_state_simulation = SteadyStateSimulation()
        steady_state_simulation.fiber = self.fiber
        steady_state_simulation.add_cw_signal(wl=self.signal_wl, power=self.signal_power)
        steady_state_simulation.add_backward_pump(wl=self.pump_wl, power=self.pump_power/2)
        steady_state_simulation.add_forward_pump(wl=self.pump_wl, power=self.pump_power/2)
        steady_state_simulation.add_ase(wl_start=1020e-9, wl_end=1040e-9, n_bins=3)
        steady_state_result = steady_state_simulation.run(tol=1e-5)

        dynamic_simulation = DynamicSimulation(self.time_steps)
        dynamic_simulation.fiber = self.fiber
        dynamic_simulation.add_forward_signal(wl=self.signal_wl, input_power=self.signal_power)
        dynamic_simulation.add_backward_pump(wl=self.pump_wl, input_power=self.pump_power/2)
        dynamic_simulation.add_forward_pump(wl=self.pump_wl, input_power=self.pump_power/2)
        dynamic_simulation.add_ase(wl_start=1020e-9, wl_end=1040e-9, n_bins=3)

        dynamic_simulation.use_cpp_backend()
        cpp_result = dynamic_simulation.run(z_nodes=self.z_nodes, dt=self.steady_state_dt, stop_at_steady_state=True)

        dynamic_simulation.use_python_backend()
        python_result = dynamic_simulation.run(z_nodes=self.z_nodes, dt=self.steady_state_dt, stop_at_steady_state=True)

        steady_state_output_powers = steady_state_result.powers_at_fiber_end()
        cpp_output_powers = cpp_result.powers_at_fiber_end()
        python_output_powers = python_result.powers_at_fiber_end()
        self.assertTrue(np.allclose(steady_state_output_powers, cpp_output_powers, rtol=1e-3))
        self.assertTrue(np.allclose(cpp_output_powers, python_output_powers, rtol=1e-6))

    def test_steady_state_python_and_cpp_two_rings(self):
        dynamic_simulation = DynamicSimulation(self.time_steps)
        fiber_with_rings = deepcopy(self.fiber)
        fiber_with_rings.set_doping_profile(ion_number_densities=[self.nt, self.nt],
                                            radii=[self.fiber.core_radius/2, self.fiber.core_radius])
        dynamic_simulation.fiber = fiber_with_rings
        dynamic_simulation.add_forward_signal(wl=self.signal_wl, input_power=self.signal_power)
        dynamic_simulation.add_backward_pump(wl=self.pump_wl, input_power=self.pump_power / 2)
        dynamic_simulation.add_forward_pump(wl=self.pump_wl, input_power=self.pump_power / 2)
        dynamic_simulation.add_ase(wl_start=1020e-9, wl_end=1040e-9, n_bins=3)

        dynamic_simulation.use_cpp_backend()
        cpp_result = dynamic_simulation.run(z_nodes=self.z_nodes, dt=self.steady_state_dt, stop_at_steady_state=True)

        dynamic_simulation.use_python_backend()
        python_result = dynamic_simulation.run(z_nodes=self.z_nodes, dt=self.steady_state_dt, stop_at_steady_state=True)

        cpp_output_powers = cpp_result.powers_at_fiber_end()
        python_output_powers = python_result.powers_at_fiber_end()
        expected_output_regression = np.array([1.12232229e-01, 2.42212332e-01, 1.13232893e-07,
                                               1.17682271e-07, 9.16464383e-08, 2.42210013e-01,
                                               1.13234548e-07, 1.17682690e-07, 9.16458631e-08])
        self.assertTrue(np.allclose(cpp_output_powers, python_output_powers, rtol=1e-6))
        self.assertTrue(np.allclose(cpp_output_powers, expected_output_regression, rtol=1e-6))

    def test_steady_state_python_and_cpp_preset_areas_and_overlaps(self):
        dynamic_simulation = DynamicSimulation(self.time_steps)
        fiber_with_rings = deepcopy(self.fiber)
        r = self.fiber.core_radius
        areas = np.pi * (np.array([r/2, r])**2 - np.array([0, r/2])**2)
        overlaps = [0.5, 0.2]
        fiber_with_rings.set_doping_profile(ion_number_densities=[self.nt, self.nt], areas=areas)
        dynamic_simulation.fiber = fiber_with_rings
        dynamic_simulation.add_forward_signal(wl=self.signal_wl,
                                              input_power=self.signal_power,
                                              mode_shape_parameters={'overlaps': overlaps})
        dynamic_simulation.add_backward_pump(wl=self.pump_wl,
                                             input_power=self.pump_power / 2,
                                             mode_shape_parameters={'overlaps': overlaps})
        dynamic_simulation.add_forward_pump(wl=self.pump_wl,
                                            input_power=self.pump_power / 2,
                                            mode_shape_parameters={'overlaps': overlaps})

        dynamic_simulation.use_cpp_backend()
        cpp_result = dynamic_simulation.run(z_nodes=self.z_nodes,
                                            dt=self.steady_state_dt/10,
                                            stop_at_steady_state=True)

        dynamic_simulation.use_python_backend()
        python_result = dynamic_simulation.run(z_nodes=self.z_nodes,
                                               dt=self.steady_state_dt/10,
                                               stop_at_steady_state=True)

        expected_output_regression = np.array([0.1166232, 0.23989275, 0.23988858])
        cpp_output_powers = cpp_result.powers_at_fiber_end()
        python_output_powers = python_result.powers_at_fiber_end()
        self.assertTrue(np.allclose(cpp_output_powers, python_output_powers, rtol=1e-6))
        self.assertTrue(np.allclose(cpp_output_powers, expected_output_regression, rtol=1e-6))

    def test_steady_state_reflection(self):
        dynamic_simulation = DynamicSimulation(self.time_steps)
        dynamic_simulation.fiber = self.fiber
        dynamic_simulation.add_forward_signal(wl=self.signal_wl,
                                              input_power=self.signal_power,
                                              label='forward_signal',
                                              reflection_target='reflected_signal',
                                              reflectance=0.04)
        dynamic_simulation.add_backward_signal(wl=self.signal_wl,
                                               input_power=1e-15,
                                               label='reflected_signal')
        dynamic_simulation.add_backward_pump(wl=self.pump_wl,
                                             input_power=self.pump_power)

        dynamic_simulation.use_cpp_backend()
        cpp_res = dynamic_simulation.run(z_nodes=self.z_nodes,
                                         dt=self.steady_state_dt,
                                         stop_at_steady_state=True)

        dynamic_simulation.use_python_backend()
        python_res = dynamic_simulation.run(z_nodes=self.z_nodes,
                                            dt=self.steady_state_dt,
                                            stop_at_steady_state=True)

        cpp_output = cpp_res.powers_at_fiber_end()
        python_output = python_res.powers_at_fiber_end()
        expected_output = np.array([0.1122059, 0.00503606, 0.48387128])
        self.assertTrue(np.allclose(cpp_output, expected_output, rtol=1e-6))
        self.assertTrue(np.allclose(cpp_output, python_output, rtol=1e-6))
