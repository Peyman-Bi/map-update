
class Viterbi:
    def __init__(self, hmm, emission_probability, priors=None, constraint_length=10, candidate_states=None, smallV=0.00000000001, counter=0, len_sum=0):
        # note: Sets the stage for running the viterbi algorithm.
        #  hmm -- a map { state_id : [(next_state1, probability), (next_state2, probability)]}
        #  priors -- a map { state_id : probability } where the sum of probabilities=1
        #  emission_probability -- a function(state_id, observation) -> [0..1]
        #  constraint_length -- how many steps into the past to consider
        #  candidate_states -- a function f(obs) that returns a set of state ids given an observation

        self.counter = counter
        self.len_sum = len_sum

        self.hmm = hmm
        self.emission_probability = emission_probability
        self.constraint_length = constraint_length
        if candidate_states:
            self.candidate_states = candidate_states
        else:
            self.candidate_states = lambda obs: list(self.hmm.keys())
            
        if not priors:
            self.priors = {}
            for state in self.hmm:
                self.priors[state] = 1.0/len(self.hmm)
        else:
            self.priors = priors

        # set up the 'incoming' reverse index: for each state, what states contribute to its probability?
        self.incoming = {}
        
        for from_state in hmm:
            for to_state, probability in hmm[from_state]:                
                if to_state not in self.incoming:
                    self.incoming[to_state]={}
                self.incoming[to_state][from_state] = probability

        self.smallV = smallV

    def step(self, obs, V=None, path={}):
        """ performs viterbi matching. updates matrix V based on a single observation """

        # if no priors are specified, make them uniform 
        if V == None:
            V = dict(self.priors)
        newV = {}
        newPath = {}

        # states that the current observation could in some way support
        state_eps = [(state, self.emission_probability(state, obs)) for state in self.candidate_states(obs)]
        nonzero_eps = [state_ep for state_ep in state_eps if state_ep[1] > 0]


        # for each candidate state, calculate its maximum probability path
        for to_state, emission_probability in nonzero_eps:
            
            # some states may have millions of incoming edges
            if len(self.incoming[to_state]) < len(V):
                nonzero_incoming = [from_state_probability for from_state_probability in iter(self.incoming[to_state].items()) if from_state_probability[0] in V and V[from_state_probability[0]]>0]
            else:
                nonzero_incoming_without_p = [from_state for from_state in V if from_state in self.incoming[to_state]]
                nonzero_incoming = [(from_state, self.incoming[to_state][from_state]) for from_state in nonzero_incoming_without_p]
            
            # list of previous possible states and their probabilities (prob, state)
            from_probs = [(V[from_state_transition_probability[0]]*emission_probability*from_state_transition_probability[1], from_state_transition_probability[0]) for from_state_transition_probability in nonzero_incoming]
            
            if len(from_probs) > 0:
                max_prob, max_from = max(from_probs, key=lambda x: x[0])
                newV[to_state] = max_prob

                # make sure we don't grow paths beyond the constraint length
                if max_from not in path:
                    path[max_from] = []
                if len(path[max_from]) == self.constraint_length:
                    path[max_from].pop(0)
                self.counter += 1
                self.len_sum += len(path[max_from])

                newPath[to_state] = path[max_from] + [to_state]
        
        newV = self.normalize(newV)
        
        small = [x for x in newV if newV[x] < self.smallV]
        for state in small:
            del newV[state]
            # jakob: this seems iffy, there should be no V for which there is no path
            if state in newPath:
                del newPath[state]

        return newV, newPath

        
    def normalize(self,V):
        """ normalizes viterbi matrix V, so that the sum of probabilities add up to 1 """
        sumProb = sum(V.values())
        
        # if we're stuck with no probability mass, return to priors instead
        if sumProb == 0: 
            return dict(self.priors)

        ret = dict([(state, V[state]/sumProb) for state in V])
        return ret