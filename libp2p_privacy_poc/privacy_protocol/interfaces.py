"""
⚠️ DRAFT — requires crypto review before production use

Proof trait interfaces for zero-knowledge proof backends.

This is a PROTOTYPE implementation for testing and validation.
DO NOT use in production without security audit.

This module provides abstract interfaces that define the contract for
proof backends, commitment schemes, and proof generation/verification.

Design Principles:
1. Abstract Base Classes (ABC) for concrete inheritance
2. Protocols for structural subtyping (duck typing)
3. Type safety with complete type hints
4. Clear separation of concerns
5. Context manager support for resource management

Interfaces:
- ProofBackend: Base class for all proof backends
- CommitmentScheme: Protocol for commitment schemes (e.g., Pedersen)
- ProofGenerator: Protocol for proof generation
- ProofVerifier: Protocol for proof verification
- AnonymitySetBackend: Interface for anonymity set proofs
- CommitmentOpeningBackend: Interface for commitment opening PoK proofs
- RangeProofBackend: Interface for range proofs
- ZKProofBackend: Composed interface for full ZK systems
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, Dict, Any, Optional
from .types import ZKProof, ProofContext


# ============================================================================
# CORE ABSTRACT BASE CLASS
# ============================================================================


class ProofBackend(ABC):
    """
    Abstract base class for zero-knowledge proof backends.

    ⚠️ REQUIRES CRYPTO REVIEW

    All proof backends must inherit from this class and implement
    the abstract methods. This ensures consistent API across different
    cryptographic backends (Pedersen, Groth16, PLONK, etc.).

    Lifecycle:
        1. Backend initialized with configuration
        2. Context manager entered (setup resources)
        3. Proofs generated and verified
        4. Context manager exited (cleanup resources)

    Thread Safety:
        - Implementations MUST be thread-safe
        - Use locks for shared state
        - Randomness sources MUST be fork-safe

    Example:
        >>> class PedersenBackend(ProofBackend):
        ...     def generate_proof(self, context, witness, public_inputs):
        ...         # Implementation
        ...         pass
        >>>
        >>> with PedersenBackend() as backend:
        ...     proof = backend.generate_proof(ctx, witness, inputs)
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """
        Human-readable name of the backend.

        Returns:
            str: Backend name (e.g., "Pedersen+Schnorr", "Groth16")
        """
        pass

    @property
    @abstractmethod
    def backend_version(self) -> str:
        """
        Version string for the backend implementation.

        Should follow semantic versioning (MAJOR.MINOR.PATCH).

        Returns:
            str: Version string (e.g., "1.0.0")
        """
        pass

    @abstractmethod
    def generate_proof(
        self,
        context: ProofContext,
        witness: Dict[str, Any],
        public_inputs: Dict[str, Any],
    ) -> ZKProof:
        """
        Generate a zero-knowledge proof.

        ⚠️ SECURITY CRITICAL

        The witness MUST remain secret. Implementations must:
        1. Validate all inputs
        2. Use constant-time operations where applicable
        3. Clear sensitive data after use
        4. Use cryptographically secure randomness
        5. Include domain separation in Fiat-Shamir

        Args:
            context: Proof context (peer_id, session_id, etc.)
            witness: Secret witness data (MUST NOT leak)
            public_inputs: Public parameters and inputs

        Returns:
            ZKProof: Generated proof with commitment, challenge, response

        Raises:
            CryptographicError: If proof generation fails
            ValueError: If inputs are invalid
            SecurityError: If security requirements are violated
        """
        pass

    @abstractmethod
    def verify_proof(
        self, proof: ZKProof, public_inputs: Dict[str, Any]
    ) -> bool:
        """
        Verify a zero-knowledge proof.

        ⚠️ SECURITY CRITICAL

        Verification MUST be complete and sound. Implementations must:
        1. Validate proof structure
        2. Recompute Fiat-Shamir challenge
        3. Verify cryptographic equation
        4. Check all public inputs
        5. Reject invalid proofs

        Args:
            proof: The proof to verify
            public_inputs: Public parameters and inputs

        Returns:
            bool: True if proof is valid, False otherwise

        Raises:
            CryptographicError: If verification computation fails
            ValueError: If inputs are invalid

        Note:
            This method MUST NOT leak information about WHY a proof
            is invalid (timing, error messages, etc.)
        """
        pass

    @abstractmethod
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the backend.

        Returns:
            dict: Backend metadata including:
                - name: Backend name
                - version: Backend version
                - curve: Elliptic curve used (if applicable)
                - library: Cryptographic library
                - features: Supported features
                - performance: Performance characteristics

        Example:
            >>> info = backend.get_backend_info()
            >>> print(info["name"], info["version"])
            Pedersen+Schnorr 1.0.0
        """
        pass

    # Context manager support (optional override)

    def __enter__(self):
        """
        Enter context manager (setup resources).

        Override this method to perform setup operations:
        - Initialize cryptographic state
        - Allocate resources
        - Verify library availability

        Returns:
            self: The backend instance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context manager (cleanup resources).

        Override this method to perform cleanup:
        - Clear sensitive data
        - Release resources
        - Close connections

        Args:
            exc_type: Exception type (if raised)
            exc_val: Exception value (if raised)
            exc_tb: Exception traceback (if raised)

        Returns:
            bool: False to propagate exceptions
        """
        return False


# ============================================================================
# COMMITMENT SCHEME PROTOCOL
# ============================================================================


@runtime_checkable
class CommitmentScheme(Protocol):
    """
    Protocol for cryptographic commitment schemes.

    ⚠️ REQUIRES CRYPTO REVIEW

    A commitment scheme allows a party to commit to a value while keeping
    it secret, with the ability to reveal it later. The scheme must be:
    1. Hiding: Commitment reveals nothing about the value
    2. Binding: Cannot change value after commitment

    This protocol defines the interface for schemes like:
    - Pedersen commitments (homomorphic, elliptic curve)
    - Hash-based commitments (simple, quantum-resistant)
    - Polynomial commitments (for SNARKs)

    Example Implementation:
        >>> class PedersenCommitment:
        ...     def commit(self, value: int, blinding_factor: bytes) -> bytes:
        ...         # C = v*G + r*H
        ...         return commitment_bytes
        ...
        ...     def verify_commitment(
        ...         self, commitment: bytes,
        ...         value: int, blinding_factor: bytes
        ...     ) -> bool:
        ...         # Recompute and compare
        ...         return computed == commitment
    """

    def commit(
        self, value: Any, blinding_factor: Optional[bytes] = None
    ) -> bytes:
        """
        Create a cryptographic commitment to a value.

        ⚠️ SECURITY CRITICAL

        The blinding factor MUST be:
        1. Cryptographically random
        2. Unique for each commitment
        3. Kept secret until reveal
        4. Generated using fork-safe randomness

        Args:
            value: The value to commit to (type depends on scheme)
            blinding_factor: Random blinding (generated if None)

        Returns:
            bytes: The commitment (deterministic given value + blinding)

        Raises:
            ValueError: If value is invalid for the scheme
            CryptographicError: If commitment generation fails
        """
        ...

    def verify_commitment(
        self, commitment: bytes, value: Any, blinding_factor: bytes
    ) -> bool:
        """
        Verify that a commitment matches a value and blinding factor.

        ⚠️ SECURITY CRITICAL

        Verification MUST be constant-time to prevent timing attacks.

        Args:
            commitment: The commitment to verify
            value: The claimed value
            blinding_factor: The blinding factor used

        Returns:
            bool: True if commitment matches, False otherwise

        Note:
            MUST NOT leak information about WHY verification failed
        """
        ...


# ============================================================================
# PROOF GENERATOR PROTOCOL
# ============================================================================


@runtime_checkable
class ProofGenerator(Protocol):
    """
    Protocol for proof generation.

    ⚠️ REQUIRES CRYPTO REVIEW

    Separates proof generation logic from backend implementation,
    enabling composition and testing.

    Example:
        >>> class SchnorrProofGenerator:
        ...     def generate(self, context, witness, public_inputs):
        ...         # 1. Commit (k*G)
        ...         # 2. Challenge (Fiat-Shamir)
        ...         # 3. Response (k + c*x)
        ...         return ZKProof(...)
    """

    def generate(
        self,
        context: ProofContext,
        witness: Dict[str, Any],
        public_inputs: Dict[str, Any],
    ) -> ZKProof:
        """
        Generate a zero-knowledge proof.

        ⚠️ WITNESS MUST REMAIN SECRET

        Args:
            context: Proof context for domain separation
            witness: Secret witness (MUST NOT leak)
            public_inputs: Public parameters

        Returns:
            ZKProof: Generated proof

        Raises:
            CryptographicError: If proof generation fails
            ValueError: If inputs are invalid
        """
        ...


# ============================================================================
# PROOF VERIFIER PROTOCOL
# ============================================================================


@runtime_checkable
class ProofVerifier(Protocol):
    """
    Protocol for proof verification.

    ⚠️ REQUIRES CRYPTO REVIEW

    Separates verification logic from backend implementation.

    Example:
        >>> class SchnorrProofVerifier:
        ...     def verify(self, proof, public_inputs):
        ...         # 1. Recompute challenge
        ...         # 2. Check equation: s*G = R + c*P
        ...         return is_valid
    """

    def verify(self, proof: ZKProof, public_inputs: Dict[str, Any]) -> bool:
        """
        Verify a zero-knowledge proof.

        ⚠️ MUST NOT LEAK WHY PROOF IS INVALID

        Args:
            proof: The proof to verify
            public_inputs: Public parameters

        Returns:
            bool: True if valid, False otherwise

        Raises:
            CryptographicError: If verification computation fails
        """
        ...


# ============================================================================
# SPECIFIC BACKEND INTERFACES
# ============================================================================


class AnonymitySetBackend(ProofBackend):
    """
    Backend for anonymity set membership proofs.

    ⚠️ REQUIRES CRYPTO REVIEW

    Proves that a peer belongs to an anonymity set without revealing
    which member they are. Uses ring signatures or similar techniques.

    Example Use Case:
        Prove "I am one of these 100 peers" without revealing which one.

    Additional Methods:
        - setup_anonymity_set(members): Configure the anonymity set
        - add_member(member): Add a member to the set
        - remove_member(member): Remove a member from the set
    """

    @abstractmethod
    def setup_anonymity_set(
        self, members: list, parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the anonymity set.

        Args:
            members: List of public keys or identifiers
            parameters: Optional configuration

        Raises:
            ValueError: If members list is invalid
            CryptographicError: If setup fails
        """
        pass


class CommitmentOpeningBackend(ProofBackend):
    """
    Backend for commitment opening proofs of knowledge.

    ⚠️ REQUIRES CRYPTO REVIEW

    Proves knowledge of a commitment opening (value, blinding)
    without revealing the witness.
    """

    @abstractmethod
    def generate_commitment_opening_proof(
        self, ctx: ProofContext
    ) -> ZKProof:
        """
        Generate a proof of knowledge for a commitment opening.

        Args:
            ctx: Proof context (must include session_id for binding)

        Returns:
            ZKProof: Commitment opening proof
        """
        pass


class RangeProofBackend(ProofBackend):
    """
    Backend for range proofs.

    ⚠️ REQUIRES CRYPTO REVIEW

    Proves that a committed value lies within a specified range
    without revealing the exact value. Uses Bulletproofs or similar.

    Example Use Case:
        Prove "My age is between 18 and 65" without revealing exact age.

    Additional Methods:
        - set_range(min_val, max_val): Configure the valid range
    """

    @abstractmethod
    def set_range(self, min_value: int, max_value: int) -> None:
        """
        Configure the valid range for proofs.

        Args:
            min_value: Minimum valid value (inclusive)
            max_value: Maximum valid value (inclusive)

        Raises:
            ValueError: If range is invalid (min >= max)
        """
        pass


class ZKProofBackend(ProofBackend):
    """
    Composed interface for complete zero-knowledge proof systems.

    ⚠️ REQUIRES CRYPTO REVIEW

    Combines multiple proof types into a unified backend supporting:
    - Commitments (Pedersen)
    - Proofs of knowledge (Schnorr)
    - Set membership (anonymity sets)
    - Range proofs
    - Custom circuit proofs (future)

    This is the main interface for production use.

    Example:
        >>> backend = PedersenZKBackend()
        >>> with backend:
        ...     # Generate commitment
        ...     commitment = backend.commit(value, blinding)
        ...     # Generate proof of knowledge
        ...     proof = backend.generate_proof(ctx, witness, inputs)
        ...     # Verify proof
        ...     assert backend.verify_proof(proof, inputs)
    """

    @abstractmethod
    def get_commitment_scheme(self) -> CommitmentScheme:
        """
        Get the commitment scheme used by this backend.

        Returns:
            CommitmentScheme: The commitment scheme instance
        """
        pass

    @abstractmethod
    def get_proof_generator(self) -> ProofGenerator:
        """
        Get the proof generator for this backend.

        Returns:
            ProofGenerator: The proof generator instance
        """
        pass

    @abstractmethod
    def get_proof_verifier(self) -> ProofVerifier:
        """
        Get the proof verifier for this backend.

        Returns:
            ProofVerifier: The proof verifier instance
        """
        pass


# ============================================================================
# TYPE HELPERS
# ============================================================================


def is_proof_backend(obj: Any) -> bool:
    """
    Check if an object implements the ProofBackend interface.

    Args:
        obj: Object to check

    Returns:
        bool: True if obj is a ProofBackend instance
    """
    return isinstance(obj, ProofBackend)


def is_commitment_scheme(obj: Any) -> bool:
    """
    Check if an object implements the CommitmentScheme protocol.

    Args:
        obj: Object to check

    Returns:
        bool: True if obj implements CommitmentScheme
    """
    return isinstance(obj, CommitmentScheme)


def is_proof_generator(obj: Any) -> bool:
    """
    Check if an object implements the ProofGenerator protocol.

    Args:
        obj: Object to check

    Returns:
        bool: True if obj implements ProofGenerator
    """
    return isinstance(obj, ProofGenerator)


def is_proof_verifier(obj: Any) -> bool:
    """
    Check if an object implements the ProofVerifier protocol.

    Args:
        obj: Object to check

    Returns:
        bool: True if obj implements ProofVerifier
    """
    return isinstance(obj, ProofVerifier)
