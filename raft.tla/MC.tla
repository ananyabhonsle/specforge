------------------------------- MODULE MC -------------------------------
EXTENDS raft

CONSTANTS MaxTerm, MaxLogLen

\* Bound the state space so TLC terminates in seconds, not hours.
\* Real Raft has unbounded terms and logs; TLC needs finite bounds.
StateConstraint ==
    /\ \A s \in Server : currentTerm[s] <= MaxTerm
    /\ \A s \in Server : Len(log[s]) <= MaxLogLen

=========================================================================
