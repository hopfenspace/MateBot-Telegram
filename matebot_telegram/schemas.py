"""
MateBot schemas used for exchanging structured data
"""

from typing import List, Optional

import pydantic


class Token(pydantic.BaseModel):
    access_token: str
    token_type: str


class Alias(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)


class Application(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    community_user: Alias
    created: pydantic.NonNegativeInt


class User(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: Optional[pydantic.constr(max_length=255)]
    balance: int
    permission: bool
    active: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]
    aliases: List[Alias]
    created: pydantic.NonNegativeInt
    accessed: pydantic.NonNegativeInt


class Transaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    sender: pydantic.NonNegativeInt
    receiver: pydantic.NonNegativeInt
    amount: pydantic.NonNegativeInt
    reason: Optional[pydantic.constr(max_length=255)]
    multi_transaction: Optional[pydantic.NonNegativeInt]
    timestamp: pydantic.NonNegativeInt


class MultiTransaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    base_amount: pydantic.NonNegativeInt
    total_amount: pydantic.NonNegativeInt
    transactions: List[Transaction]
    timestamp: pydantic.NonNegativeInt


class Consumable(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    description: pydantic.constr(max_length=255)
    price: pydantic.PositiveInt
    messages: List[pydantic.constr(max_length=255)]
    symbol: pydantic.constr(min_length=1, max_length=1)
    stock: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt


class Consumption(pydantic.BaseModel):
    user: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    consumable_id: pydantic.NonNegativeInt
    adjust_stock: bool
    respect_stock: bool


class Vote(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)
    modified: pydantic.NonNegativeInt


class Ballot(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    question: pydantic.constr(max_length=255)
    changeable: bool
    active: bool
    votes: List[Vote]
    result: Optional[int]
    closed: Optional[pydantic.NonNegativeInt]


class Refund(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    allowed: Optional[bool]
    ballot: pydantic.NonNegativeInt
    transaction: Optional[Transaction]
    created: Optional[pydantic.NonNegativeInt]
    accessed: Optional[pydantic.NonNegativeInt]


class CommunismUserBinding(pydantic.BaseModel):
    user: pydantic.NonNegativeInt
    quantity: pydantic.NonNegativeInt


class Communism(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    accepted: Optional[bool]
    externals: pydantic.NonNegativeInt
    created: pydantic.NonNegativeInt
    accessed: pydantic.NonNegativeInt
    participants: List[CommunismUserBinding]
    transactions: Optional[List[Transaction]]


class Callback(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    base: pydantic.stricturl(max_length=255, tld_required=False)
    app: Optional[pydantic.NonNegativeInt]
    username: Optional[pydantic.constr(max_length=255)]
    password: Optional[pydantic.constr(max_length=255)]


class GeneralConfig(pydantic.BaseModel):
    min_refund_approves: pydantic.PositiveInt
    min_refund_disapproves: pydantic.PositiveInt
    max_parallel_debtors: pydantic.PositiveInt
    max_simultaneous_consumption: pydantic.NonNegativeInt
    max_transaction_amount: pydantic.NonNegativeInt
