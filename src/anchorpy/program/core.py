"""This module defines the Program class."""
from __future__ import annotations
from typing import Any, Optional
from base64 import b64decode
import zlib
import json

from anchorpy.coder.coder import Coder
from anchorpy.coder.accounts import ACCOUNT_DISCRIMINATOR_SIZE
from anchorpy.program.common import AddressType, translate_address
from anchorpy.idl import Idl, decode_idl_account, idl_address
from solana.publickey import PublicKey
from anchorpy.provider import Provider
from anchorpy.program.namespace.rpc import (
    RpcFn,
    build_rpc_item,
)
from anchorpy.program.namespace.transaction import (
    TransactionFn,
    build_transaction_fn,
)
from anchorpy.program.namespace.instruction import (
    InstructionFn,
)
from anchorpy.program.namespace.account import AccountClient, build_account
from anchorpy.program.namespace.simulate import (
    SimulateFn,
    build_simulate_item,
)
from anchorpy.program.namespace.types import build_types


class IdlNotFoundError(Exception):
    """Raise when requested IDL account does not exist."""


def _parse_idl_errors(idl: Idl) -> dict[int, str]:
    """Turn IDL errors into something readable.

    Uses message if available, otherwise name.

    Args:
        idl: Parsed `Idl` instance.

    """
    errors = {}
    for e in idl.errors:
        msg = e.msg if e.msg else e.name
        errors[e.code] = msg
    return errors


def _build_namespace(  # noqa: WPS320
    idl: Idl,
    coder: Coder,
    program_id: PublicKey,
    provider: Provider,
) -> tuple[
    dict[str, RpcFn],
    dict[str, InstructionFn],
    dict[str, TransactionFn],
    dict[str, AccountClient],
    dict[str, SimulateFn],
    dict[str, Any],
]:
    """Generate all namespaces for a given program.

    Args:
        idl: The parsed IDL object.
        coder: The program's Coder object .
        program_id: The Program ID.
        provider: The program's provider.

    Returns:
        The program namespaces.
    """
    idl_errors = _parse_idl_errors(idl)

    rpc = {}
    instruction = {}
    transaction = {}
    simulate = {}

    for idl_ix in idl.instructions:

        ix_item = InstructionFn(idl_ix, coder.instruction.build, program_id)
        tx_item = build_transaction_fn(idl_ix, ix_item)
        rpc_item = build_rpc_item(idl_ix, tx_item, idl_errors, provider)
        simulate_item = build_simulate_item(
            idl_ix,
            tx_item,
            idl_errors,
            provider,
            coder,
            program_id,
            idl,
        )

        name = idl_ix.name
        instruction[name] = ix_item
        transaction[name] = tx_item
        rpc[name] = rpc_item
        simulate[name] = simulate_item

    account = build_account(idl, coder, program_id, provider) if idl.accounts else {}
    types = build_types(idl)
    return rpc, instruction, transaction, account, simulate, types


def _pako_inflate(data):
    # https://stackoverflow.com/questions/46351275/using-pako-deflate-with-python
    decompress = zlib.decompressobj(15)
    decompressed_data = decompress.decompress(data)
    decompressed_data += decompress.flush()
    return decompressed_data


class Program(object):
    """Program provides the IDL deserialized client representation of an Anchor program.

    This API is the one stop shop for all things related to communicating with
    on-chain programs. Among other things, one can send transactions, fetch
    deserialized accounts, decode instruction data, subscribe to account
    changes, and listen to events.

    In addition to field accessors and methods, the object provides a set of
    dynamically generated properties, also known as namespaces, that
    map one-to-one to program methods and accounts.

    """

    def __init__(
        self, idl: Idl, program_id: PublicKey, provider: Optional[Provider] = None
    ):
        """Initialize the Program object.

        Args:
            idl: The parsed IDL object.
            program_id: The program ID.
            provider: The Provider object for the Program. Defaults to Provider.local().
        """
        self.idl = idl
        self.program_id = program_id
        self.provider = provider if provider is not None else Provider.local()
        self.coder = Coder(idl)

        (  # noqa: WPS236
            rpc,
            instruction,
            transaction,
            account,
            simulate,
            types,
        ) = _build_namespace(
            idl,
            self.coder,
            program_id,
            self.provider,
        )

        self.rpc = rpc
        self.instruction = instruction
        self.transaction = transaction
        self.account = account
        self.simulate = simulate
        self.type = types

    async def __aenter__(self) -> Program:
        """Use as a context manager."""
        await self.provider.__aenter__()  # noqa: WPS609
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        """Exit the context manager."""
        await self.close()

    async def close(self) -> None:
        """Use this when you are done with the client."""
        await self.provider.close()

    @classmethod
    async def fetch_idl(
        cls,
        address: AddressType,
        provider,
    ) -> Idl:
        """Fetch an idl from the blockchain.

        Args:
            address: The program ID.
            provider: The network and wallet context.

        Raises:
            IdlNotFoundError: If the requested IDL account does not exist.

        Returns:
            Idl: The fetched IDL.
        """
        program_id = translate_address(address)
        actual_provider = provider if provider is not None else Provider.local()
        idl_addr = idl_address(program_id)
        account_info = await actual_provider.connection.get_account_info(idl_addr)
        account_info_val = account_info["result"]["value"]
        if account_info_val is None:
            raise IdlNotFoundError(f"IDL not found for program: {address}")
        idl_account = decode_idl_account(
            b64decode(account_info_val["data"][0])[ACCOUNT_DISCRIMINATOR_SIZE:]
        )
        inflated_idl = _pako_inflate(bytes(idl_account["data"])).decode()
        return Idl.from_json(json.loads(inflated_idl))

    @classmethod
    async def at(
        cls,
        address: AddressType,
        provider: Optional[Provider] = None,
    ) -> Program:
        """Generate a Program client by fetching the IDL from the network.

        In order to use this method, an IDL must have been previously initialized
        via the anchor CLI's `anchor idl init` command.

        Args:
            address: The program ID.
            provider: The network and wallet context.

        Returns:
            The Program instantiated using the fetched IDL.
        """
        program_id = translate_address(address)
        idl = await cls.fetch_idl(program_id, provider)
        return cls(idl, program_id, provider)
