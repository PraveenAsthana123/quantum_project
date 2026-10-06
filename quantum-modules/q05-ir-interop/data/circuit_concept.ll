; QIR (Quantum Intermediate Representation) — LLVM IR format
; Circuit: 3-qubit GHZ state
; Reference: https://github.com/qir-alliance/qir-spec

@__quantum__rt__qubit_allocate_array = external global {}
declare void @__quantum__qis__h__body(%Qubit*)
declare void @__quantum__qis__cnot__body(%Qubit*, %Qubit*)
declare void @__quantum__qis__mz__body(%Qubit*, %Result*)

%Qubit = type opaque
%Result = type opaque

define void @ghz_circuit() {{
entry:
  ; Allocate qubits
  %q0 = call %Qubit* @__quantum__rt__qubit_allocate()
  %q1 = call %Qubit* @__quantum__rt__qubit_allocate()
  %q2 = call %Qubit* @__quantum__rt__qubit_allocate()
  %r0 = call %Result* @__quantum__rt__result_allocate()
  %r1 = call %Result* @__quantum__rt__result_allocate()
  %r2 = call %Result* @__quantum__rt__result_allocate()

  ; GHZ circuit
  call void @__quantum__qis__h__body(%Qubit* %q0)
  call void @__quantum__qis__cnot__body(%Qubit* %q0, %Qubit* %q1)
  call void @__quantum__qis__cnot__body(%Qubit* %q1, %Qubit* %q2)

  ; Measure
  call void @__quantum__qis__mz__body(%Qubit* %q0, %Result* %r0)
  call void @__quantum__qis__mz__body(%Qubit* %q1, %Result* %r1)
  call void @__quantum__qis__mz__body(%Qubit* %q2, %Result* %r2)

  ret void
}}
