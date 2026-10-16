---- MODULE raft_llm_bug ----

EXTENDS Naturals, FiniteSets

CONSTANTS Server, Follower, Candidate, Leader, Nil

VARIABLES state, currentTerm, votedFor, votesGot

(*-----------------------------------------------------------------
  Initialization
-----------------------------------------------------------------*)
Init ==
    /\ state = [s \in Server |-> Follower]
    /\ currentTerm = [s \in Server |-> 0]
    /\ votedFor = [s \in Server |-> Nil]
    /\ votesGot = [s \in Server |-> 0]

(*-----------------------------------------------------------------
  Actions
-----------------------------------------------------------------*)
BecomeCandidate(s) ==
    /\ state[s] = Follower
    /\ state' = [state EXCEPT ![s] = Candidate]
    /\ currentTerm' = [currentTerm EXCEPT ![s] = currentTerm[s] + 1]
    /\ votedFor' = [votedFor EXCEPT ![s] = s]
    /\ votesGot' = [votesGot EXCEPT ![s] = 1]
    /\ UNCHANGED << >>

BecomeLeader(s) ==
    /\ state[s] = Candidate
    \* BUG: majority check removed
    /\ state' = [state EXCEPT ![s] = Leader]
    /\ UNCHANGED << currentTerm, votedFor, votesGot >>

BecomeFollower(s, higherTerm) ==
    /\ higherTerm > currentTerm[s]
    /\ state' = [state EXCEPT ![s] = Follower]
    /\ currentTerm' = [currentTerm EXCEPT ![s] = higherTerm]
    /\ votedFor' = [votedFor EXCEPT ![s] = Nil]
    /\ UNCHANGED votesGot

(*-----------------------------------------------------------------
  Next-state relation
-----------------------------------------------------------------*)
Next ==
    \/ \E s \in Server: BecomeCandidate(s)
    \/ \E s \in Server: BecomeLeader(s)
    \/ \E s \in Server, ht \in 0..3: BecomeFollower(s, ht)

(*-----------------------------------------------------------------
  Specification
-----------------------------------------------------------------*)
Spec == Init /\ [][Next]_<<state, currentTerm, votedFor, votesGot>>

(*-----------------------------------------------------------------
  Invariant: at most one leader per term
-----------------------------------------------------------------*)
AtMostOneLeader ==
    \A i, j \in Server :
        (state[i] = Leader /\ state[j] = Leader /\ currentTerm[i] = currentTerm[j])
            => i = j


====
