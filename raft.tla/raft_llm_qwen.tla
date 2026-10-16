---- MODULE raft_llm_qwen ----

EXTENDS Naturals, FiniteSets

CONSTANTS Server, Follower, Candidate, Leader, Nil

VARIABLES state, currentTerm, votedFor, votesGot

(*
  Helper to check if a server has a majority of votes.
  In a 3-server cluster, majority is > 1, i.e., >= 2.
  We assume Server is a set of 3 elements.
*)
Majority(v) == v > (Cardinality(Server) \div 2)

Init ==
  /\ state = [s \in Server |-> Follower]
  /\ currentTerm = [s \in Server |-> 0]
  /\ votedFor = [s \in Server |-> Nil]
  /\ votesGot = [s \in Server |-> 0]

BecomeCandidate(s) ==
  /\ state[s] = Follower
  /\ state' = [state EXCEPT ![s] = Candidate]
  /\ currentTerm' = [currentTerm EXCEPT ![s] = currentTerm[s] + 1]
  /\ votedFor' = [votedFor EXCEPT ![s] = s]
  /\ votesGot' = [votesGot EXCEPT ![s] = 1]
  /\ \A t \in Server \ {s} :
      IF state[t] = Follower /\ currentTerm[t] = currentTerm[s] /\ votedFor[t] = Nil
      THEN
        /\ state'[t] = Follower
        /\ currentTerm'[t] = currentTerm[t]
        /\ votedFor'[t] = s
        /\ votesGot'[t] = votesGot[t] + 1
      ELSE
        /\ state'[t] = state[t]
        /\ currentTerm'[t] = currentTerm[t]
        /\ votedFor'[t] = votedFor[t]
        /\ votesGot'[t] = votesGot[t]

BecomeLeader(s) ==
  /\ state[s] = Candidate
  /\ Majority(votesGot[s])
  /\ state' = [state EXCEPT ![s] = Leader]
  /\ \A t \in Server \ {s} :
      IF state[t] = Follower /\ currentTerm[t] = currentTerm[s]
      THEN
        /\ state'[t] = Follower
        /\ currentTerm'[t] = currentTerm[t]
        /\ votedFor'[t] = votedFor[t]
        /\ votesGot'[t] = votesGot[t]
      ELSE
        /\ state'[t] = state[t]
        /\ currentTerm'[t] = currentTerm[t]
        /\ votedFor'[t] = votedFor[t]
        /\ votesGot'[t] = votesGot[t]

BecomeFollower(s, higherTerm) ==
  /\ higherTerm > currentTerm[s]
  /\ state' = [state EXCEPT ![s] = Follower]
  /\ currentTerm' = [currentTerm EXCEPT ![s] = higherTerm]
  /\ votedFor' = [votedFor EXCEPT ![s] = Nil]
  /\ votesGot' = [votesGot EXCEPT ![s] = 0]
  /\ \A t \in Server \ {s} :
      IF currentTerm[t] < higherTerm
      THEN
        /\ state'[t] = Follower
        /\ currentTerm'[t] = higherTerm
        /\ votedFor'[t] = Nil
        /\ votesGot'[t] = 0
      ELSE
        /\ state'[t] = state[t]
        /\ currentTerm'[t] = currentTerm[t]
        /\ votedFor'[t] = votedFor[t]
        /\ votesGot'[t] = votesGot[t]

Next ==
  \/ \E s \in Server : BecomeCandidate(s)
  \/ \E s \in Server : BecomeLeader(s)
  \/ \E s \in Server :
       \E t \in Server \ {s} :
         /\ state[t] = Leader
         /\ currentTerm[t] > currentTerm[s]
         /\ BecomeFollower(s, currentTerm[t])
  \/ UNCHANGED <<state, currentTerm, votedFor, votesGot>>

Spec == Init /\ [][Next]_<<state, currentTerm, votedFor, votesGot>>

AtMostOneLeader ==
  \A i, j \in Server :
    (state[i] = Leader /\ state[j] = Leader /\ currentTerm[i] = currentTerm[j])
      => i = j


====
