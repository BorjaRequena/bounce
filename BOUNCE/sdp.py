# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/06_sdp.ipynb (unless otherwise specified).

__all__ = ['picos2np', 'SdPSolver', 'SdPEnergySolver', 'SdPEnergyAndersonSolver', 'SdPEnergyUskovLichkovskiySolver',
           'SdPWitnessSolver']

# Cell
import picos
import numpy as np
from itertools import combinations
from collections.abc import Iterable
from .utils import state2str, simplify_layout

# Cell
def picos2np(variable):
    "Converts picos variable (even sparse) to numpy matrix."
    return picos.expressions.data.cvx2np(variable.value)

# Cell
class SdPSolver:
    def __init__(self, solver='cvxopt'): self.solver = solver

    def solve(self):
        raise NotImplementedError("Please define an appropiate `solve` method" +
                                  " for your problem in the `SdPSolver`.")

    def ojimetro(self):
        raise NotImplementedError("Please define a cost estimation function method" +
                                  " suitable for your problem in the `SdPSolver`.")


# Cell
class SdPEnergySolver(SdPSolver):
    """Solver to compute lower bounds of the ground state energy of local Hamiltonians. It
        follows the method described in [1] (see refs below) to formulate the objective and
        enforce the problem constraints."""

    def solve(self, interactions, layout):
        """Creates and solves the SdP associated to the given layout and Hamiltonian interactions.
        The result is a lower bound of the Hamiltonian's ground state energy."""
        layout = simplify_layout(layout)
        problem = picos.Problem(solver=self.solver)
        variables = [(sites, picos.HermitianVariable('rho'+','.join(map(str, sites)),
                                                    (2**len(sites), 2**len(sites)))) for sites in layout]
        objective = self._build_energy_objective(variables, interactions)

        compatibility_constraints = self._get_compatibility_constraints(variables)
        problem.add_list_of_constraints([rho >> 0 for _, rho in variables])
        problem.add_list_of_constraints([picos.trace(rho) == 1 for _, rho in variables])
        problem.add_list_of_constraints(compatibility_constraints)
        problem.set_objective('min', objective)

        try:
            problem.solve()
            result = np.real(objective.value)
        except:
            result = None
        return result

    @staticmethod
    def ojimetro(layout):
        "Estimates the amount of free parameters involved in the SdP associated to the `layout`."
        layout = simplify_layout(layout)
        all_variables = np.sum([2**(2*len(sites)) for sites in layout])
        intersections = []
        for k, sites1 in enumerate(layout[:-1]):
            for sites2 in layout[k+1:]:
                intersections.append(np.intersect1d(sites1, sites2))
        intersections = simplify_layout(intersections)
        dep_variables = np.sum([2**(2*len(sites)) for sites in intersections])
        return all_variables - dep_variables

    def _build_energy_objective(self, variables, interactions):
        "Builds the optimization objective: the expected energy."
        objective = 0
        for support, h in interactions:
            supported = False
            for sites, rho in variables:
                common, _, idx = np.intersect1d(support, sites, return_indices=True)
                if len(common) == len(support):
                    rdm = rho.partial_trace(self._complementary_system(idx, len(sites)))
                    objective += (rdm | h) # Tr(rdm·H')
                    supported = True
                    break
            if not supported:
                eigenvalues, _ = np.linalg.eigh(picos2np(h))
                objective += min(eigenvalues)
        return objective

    def _get_compatibility_constraints(self, variables):
        "Instantiates the compatibility constraints between the reduced density matrices."
        compatibility_constraints = []
        for k1, (sites1, rho1) in enumerate(variables):
            for k2 in range(k1+1, len(variables)):
                sites2, rho2 = variables[k2]
                common, idx1, idx2 = np.intersect1d(sites1, sites2, return_indices=True)
                if len(common) > 0:
                    partial_trace1 = rho1.partial_trace(self._complementary_system(idx1, len(sites1)))
                    partial_trace2 = rho2.partial_trace(self._complementary_system(idx2, len(sites2)))
                    constraint = partial_trace1 - partial_trace2 == 0
                    compatibility_constraints.append(constraint)
        return compatibility_constraints

    @staticmethod
    def _complementary_system(subsystem, size):
        "Obtains the complementary system of subsystem."
        return list(map(int, np.setdiff1d(np.arange(size), subsystem)))

# Cell
class SdPEnergyAndersonSolver(SdPEnergySolver):
    """Solver to compute bounds to the ground state energy of local Hamiltonians implementing the
    methods described in [2] (see references below). Finds the so-called Anderson bound. Assumes
    the system is one-dimensional."""

    def solve(self, interactions, cluster_size=3):
        "Computes the Anderson bound for a one-dimensional system with `interactions`."
        cluster_size, n_clusters = self._get_clusters(interactions, cluster_size)

        sites = np.arange(cluster_size)
        rho = picos.HermitianVariable('rho'+','.join(map(str, sites)),
                                      (2**cluster_size, 2**cluster_size))
        objective = self._build_energy_objective(sites, rho, interactions)

        problem = picos.Problem(solver=self.solver)
        problem.add_constraint(rho >> 0)
        problem.add_constraint(picos.trace(rho) == 1)
        problem.set_objective('min', objective)

        try:
            problem.solve()
            result = np.real(objective.value)
        except:
            print(problem)
            result = 0.
        return n_clusters*result

    def ojimetro(self, cluster_size):
        "Estimates the cost involved in finding the Anderson bound for the given cluster size."
        cluster_size = self._get_cluster_size(cluster_size)
        return 2**(2*cluster_size)

    def _build_energy_objective(self, sites, rho, interactions):
        objective = 0
        for support, h in interactions:
            common, _, idx = np.intersect1d(support, sites, return_indices=True)
            if len(common) == len(support):
                rdm = rho.partial_trace(self._complementary_system(idx, len(sites)))
                objective += (rdm | h) # Tr(rdm·H')
        return objective

    def _get_clusters(self, interactions, cluster_size):
        "Find the number of clusters needed for the system."
        system_size = max([s for sites, _ in interactions for s in sites]) + 1
        cluster_size = self._get_cluster_size(cluster_size)
        if system_size % (cluster_size - 1) != 0:
            raise ValueError(f"The number of qubits {system_size} must be divisible by " +
                             "cluster_size - 1.")
        else:
            n_clusters = system_size // (cluster_size - 1) # 1D nearest-neighbor interaction
        return cluster_size, n_clusters

    @staticmethod
    def _get_cluster_size(cluster_size):
        "Checks the `cluster_size` format and handles it accordingly."
        if isinstance(cluster_size, (int, float)): return int(cluster_size)
        elif isinstance(cluster_size, Iterable): return max([len(l) for l in cluster_size])
        else: raise ValueError("`cluster_size` should be an int or a layout.")

# Cell
class SdPEnergyUskovLichkovskiySolver(SdPEnergyAndersonSolver):
    """Solver to compute ground state energy bounds of local Hamiltonians. It follows the method
    introduced in [3] (see references below) to improve over the Anderson bound. The method assumes
    the reduced states have certain symmetries, such as translational invariance."""

    def solve(self, interactions, cluster_size=3):
        "Computes the Uskov and Lichkovskiy bound for a one-dimensional Hamiltonian."
        cluster_size, n_clusters = self._get_clusters(interactions, cluster_size)

        sites = np.arange(cluster_size)
        rho = picos.HermitianVariable('rho'+','.join(map(str, sites)), (2**cluster_size, 2**cluster_size))
        objective = self._build_energy_objective(sites, rho, interactions)

        symmetry_constraints = self._get_symmetry_constraints(sites, rho)
        problem = picos.Problem(solver = 'cvxopt')
        problem.add_constraint(rho >> 0)
        problem.add_constraint(picos.trace(rho) == 1)
        problem.add_list_of_constraints(symmetry_constraints)
        problem.set_objective('min', objective)

        try:
            problem.solve()
            result = np.real(objective.value)
        except:
            print(problem)
            result = 0.
        return n_clusters*result


    def _get_symmetry_constraints(self, sites, rho):
        # Symmetry constraints: TI and specular symmetry in the cluster
        x = picos.Constant('x', [[0, 1], [1, 0]])
        y = picos.Constant('y', [[0, -1j], [1j, 0]])
        z = picos.Constant('z', [[1, 0], [0, -1]])
        Id = picos.Constant('Id', [[1, 0], [0, 1]])

        def sigma_term(idx): return tensor_prod(idx, x) + tensor_prod(idx, y) + tensor_prod(idx, z)

        def tensor_prod(idx, s):
            "Tensor product of operator `s` acting on indexes `idx`. Fills rest with Id."
            matrices = [s if i in idx else Id for i in sites]
            prod = matrices[0]
            for i in range(1, len(sites)): prod = prod @ matrices[i]
            return prod

        constraints = []
        idx = [sites[i:i+2] for i in range(len(sites)-1)]
        for i in range(len(idx)//2):
            left, right = sigma_term(idx[i]), sigma_term(idx[-(i+1)])
            adj = sigma_term(idx[i+1])
            # Specular symmetry
            constraints.append((left | rho) == (right | rho)) # Tr(sigma_01*rho) = Tr(sigma_{n-1,n}*rho)
            # Translational invariance
            constraints.append((left | rho) == (adj | rho)) # Tr(sigma_01*rho) = Tr(sigma_12*rho)

        return constraints

# Cell
class SdPWitnessSolver(SdPEnergySolver):
    """Solver to detect entanglement from energy bounds. It follows the formalism described in [1]
    to obtain a lower bound of the minimum energy for separable states. If we can find a state with
    a lower energy than that, the state is entangled."""

    def solve(self, interactions, layout):
        """Creates and solves the SdP associated to the given layout and Hamiltonian interactions.
        The result is a lower bound of the minimum energy for separable states."""
        layout = simplify_layout(layout)
        problem = picos.Problem(solver=self.solver)
        variables = [(site, picos.HermitianVariable('rho'+','.join(map(str, site)),
                                                    (2**len(site), 2**len(site)))) for site in layout]
        objective = self._build_energy_objective(variables, interactions)

        compatibility_constraints = self._get_compatibility_constraints(variables)
        ppt_constraints = self._get_ppt_constraints(variables)
        problem.add_list_of_constraints([rho >> 0 for _, rho in variables])
        problem.add_list_of_constraints([picos.trace(rho) == 1 for _, rho in variables])
        problem.add_list_of_constraints(compatibility_constraints)
        problem.add_list_of_constraints(ppt_constraints)
        problem.set_objective('min', objective)

        try:
            problem.solve()
            result = np.real(objective.value)
        except:
            result = None
        return result

    @staticmethod
    def _get_ppt_constraints(variables):
        """Returns the constraints to be imposed such that the reduced density matrices are
        positive under partial transposition (PPT) to approximate the set of separable states."""
        constraints = []
        for sites, rho in variables:
            idx = np.arange(len(sites))
            for size in range(1, len(sites)):
                constraints.append([picos.partial_transpose(rho,
                                                            subsystems=map(int, subsystem)) >> 0
                                    for subsystem in combinations(idx, size)])
        return [c for rdm_constraints in constraints for c in rdm_constraints]