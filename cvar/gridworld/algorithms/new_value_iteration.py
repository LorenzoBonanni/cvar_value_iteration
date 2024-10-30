import copy

import numpy as np
from docplex.mp.model import Model
from tqdm import tqdm

from cvar.gridworld.cliffwalker import GridWorld


def value_update(world, V, id=0, alpha_set_all=None):
    V_ = copy.deepcopy(V)
    for s in tqdm(world.states(), desc='Value Update %d' % id):
        alpha_set = alpha_set_all[s.y, s.x]
        transitions = world.transitions(s)
        solver = Model(name='cvar_value')

        right_ineqs = []
        left_ineqs = []
        xi_constraints = []
        counter = 0
        objective = np.zeros((len(world.ACTIONS), len(alpha_set)))
        objectives_fn = []
        for a in world.ACTIONS:
            action_transitions = transitions[a]
            transitions_pos = []
            transitions_probabilities = []
            for trans in action_transitions:
                transitions_pos.append(trans.state)
                transitions_probabilities.append(trans.prob)

            transitions_pos = np.array(transitions_pos)
            transitions_probabilities = np.array(transitions_probabilities)
            ts = []
            for i in range(len(alpha_set) - 1):
                alpha_i = alpha_set[i]
                alpha_ip1 = alpha_set[i + 1]
                n_trans = len(transitions_pos)

                xi = np.array([solver.continuous_var(0, solver.infinity, f'xi_{counter+tnum}') for tnum in range(n_trans)])
                counter += n_trans
                t = np.array([solver.continuous_var(-1e6, 1e6, f't_{counter+tnum}') for tnum in range(n_trans)])
                counter += n_trans

                ts.append(t)
                v_i = V_[i, transitions_pos[:, 0], transitions_pos[:, 1]]
                v_ip1 = V_[i+1, transitions_pos[:, 0], transitions_pos[:, 1]]
                slope = (alpha_ip1 * v_ip1 - alpha_i * v_i) / (alpha_ip1 - alpha_i)
                right_ineq = lambda alpha_in: (alpha_i*v_i/alpha_in - slope * alpha_i/alpha_in) * transitions_probabilities
                left_ineq = t - slope * xi * transitions_probabilities
                right_ineqs.append(right_ineq)
                left_ineqs.append(left_ineq)
                xi_constraints.append(xi)
                objectives_fn.append(sum(t))
                solver.add_constraint(xi @ transitions_probabilities == 1)

            for alpha_idx, alpha in enumerate(alpha_set):
                if alpha == 0:
                    # when alpha is 0, the cvar is simply the worst case value, so no expectation over some distribution
                    transitions_pos = np.array(transitions_pos)
                    objective[a, alpha_idx] = min(V_[alpha_idx, transitions_pos[:, 0], transitions_pos[:, 1]])
                else:
                    for idx in range(len(right_ineqs)):
                        l_ineq = left_ineqs[idx]
                        r_ineq = right_ineqs[idx](alpha)
                        for idx2 in range(len(l_ineq)):
                            solver.add_constraint(l_ineq[idx2] >= r_ineq[idx2])
                            solver.add_constraint(xi_constraints[idx][idx2] <= 1/alpha)

        solver.maximize(sum(objectives_fn))
        solver.print_information()
        solution = solver.solve()
        if solution.solve_status.value == 2:
            print('Optimal solution found')
            solved_xi = []
            solved_t = []
            # TODO understand why this is not working, xi values are 1 which violates the constraints
            for v in solver.iter_variables():
                if v.name.startswith('xi'):
                    solved_xi.append(v.solution_value)
                elif v.name.startswith('t'):
                    solved_t.append(v.solution_value)
        else:
            print('No optimal solution found')
            exit(1)
    return V_


def value_iteration(world, V=None, max_iters=1e3, eps_convergence=1e-3):
    Ny = 21
    if V is None:
        V = np.zeros((Ny, world.height, world.width))
    Y_set_all = np.ones((world.height, world.width, 1)) * np.concatenate(([0], np.logspace(-2, 0, Ny-1)))
    i = 0
    figax = None
    while True:
        V_ = value_update(world, V, i, Y_set_all)

        # error, worst_state = value_difference(V, V_, world)
        # if error < eps_convergence:
        #     print("value fully learned after %d iterations" % (i,))
        #     print('Error:', error)
        #     break
        # elif i > max_iters:
        #     print("value finished without convergence after %d iterations" % (i,))
        #     break
        # V = V_
        # i += 1
        #
        # print('Iteration:{}, error={} ({})'.format(i, error, worst_state))

    return V


if __name__ == '__main__':
    import pickle
    from cvar.gridworld.plots.grid import InteractivePlotMachine, PlotMachine

    PERFORM_VI = True
    # MAX_ITERS = 40
    MAX_ITERS = 100
    TOLL = 1e-3

    np.random.seed(2)
    if PERFORM_VI:
        world = GridWorld(14, 16, random_action_p=0.05, path='gridworld3.png')
        # # world = AutonomousCarNavigation()
        V = value_iteration(world, max_iters=MAX_ITERS, eps_convergence=TOLL)
        # pickle.dump((world, V), open('data/models/vi_test.pkl', mode='wb'))

    # # ============================= load
    # world, V = pickle.load(open('data/models/vi_test.pkl', 'rb'))
    # # indexes = [2, 11, 20]
    # alphas = np.concatenate(([0], np.logspace(-2, 0, 20)))
    # # alphas = alphas[1:]
    # # ============================= RUN
    # CvarValues = [np.array([V.V[ix].cvar_alpha(alpha) for ix in np.ndindex(V.V.shape)]).reshape(V.V.shape) for alpha in alphas]
    # CvarValues = np.array(CvarValues)
    # # CvarValues = np.array([CvarValues[i].flatten(order='F') for i in range(CvarValues.shape[0])])
    # matlabValues =  -scipy.io.loadmat('data/models/value.mat')['im']
    # # CvarValues[matlabValues == 0] = 0
    # matlab_alpha1 = matlabValues[-1, :, :]
    # python_alpha1 = CvarValues[-1, :, :]
    # # print(np.isclose(matlab_alpha1, python_alpha1, atol=1e-2).all())
    # alphas = [1.0]
    # # ============================= PLOT
    # for alpha in alphas:
    #     print(alpha)
    #     pm = InteractivePlotMachine(world, V, alpha=alpha)
    #     pm.fig.savefig('data/figures/vi_{}.png'.format(alpha))
    #     # pm.show()

    # =============== VI stats
    # nb_epochs = int(100)
    # rewards_sample = []
    # for alpha in [0.1, 0.25, 0.5, 1.]:
    #     _, rewards = policy_stats(world, XiBasedPolicy(V, alpha), alpha, nb_epochs=nb_epochs)
    #     rewards_sample.append(rewards)
    # np.save('files/sample_rewards_tamar.npy', np.array(rewards_sample))
    # policy_stats(world, var_policy, alpha, nb_epochs=nb_epochs)

    # =============== plot dynamic
    # alpha = 0.5
    # V_visual = np.array([[V.V[i, j].cvar_alpha(alpha) for j in range(len(V.V[i]))] for i in range(len(V.V))])
    # # print(V_visual)
    # plot_machine = PlotMachine(world, V_visual)
    # # policy = var_policy
    # policy = XiBasedPolicy(V, alpha)
    # for i in range(10):
    #     S, A, R = epoch(world, policy, plot_machine=plot_machine)
    #     print('{}: {}'.format(i, np.sum(R)))
    #     policy.reset()