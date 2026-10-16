"""
Simplified Raft leader-election Go code — the input to the LLM.

This is a minimal but real leader-election protocol (not the full Ongaro spec).
The LLM's job: translate this into a TLA+ spec that TLC can verify.
"""

RAFT_GO_CODE = """// Raft leader election — simplified Go implementation
package raft

type ServerState int
const (
    Follower ServerState = iota
    Candidate
    Leader
)

type Server struct {
    id          int
    state       ServerState
    currentTerm int
    votedFor    int    // -1 means no vote
    votesGot    int
}

// BecomeCandidate: a follower times out and starts an election
func (s *Server) BecomeCandidate() {
    if s.state != Follower {
        return
    }
    s.state = Candidate
    s.currentTerm += 1
    s.votedFor = s.id        // vote for self
    s.votesGot = 1
}

// BecomeLeader: candidate wins the election
func (s *Server) BecomeLeader(votesReceived int, clusterSize int) {
    if s.state != Candidate {
        return
    }
    if votesReceived > clusterSize/2 {   // majority
        s.state = Leader
    }
}

// BecomeFollower: server receives higher term, steps down
func (s *Server) BecomeFollower(higherTerm int) {
    if higherTerm > s.currentTerm {
        s.state = Follower
        s.currentTerm = higherTerm
        s.votedFor = -1
    }
}
"""

# The invariant we want the LLM's spec to satisfy
TARGET_INVARIANT = """
(*
Invariant to check: at most one leader per term.
No two distinct servers can be Leader in the same term.
*)
AtMostOneLeader ==
  \\A i, j \\in Server :
    (state[i] = Leader /\\ state[j] = Leader /\\ currentTerm[i] = currentTerm[j])
      => i = j
"""

# The TLA+ module skeleton we expect the LLM to fill
EXPECTED_VARIABLES = ["state", "currentTerm", "votedFor", "votesGot"]
EXPECTED_CONSTANTS = ["Server", "Follower", "Candidate", "Leader", "Nil", "ClusterSize"]
