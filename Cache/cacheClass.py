from rest_framework_extensions.key_constructor.constructors import (
    KeyConstructor,DefaultKeyConstructor
)
from rest_framework_extensions.key_constructor import bits

class UserKeyConstructor(DefaultKeyConstructor):
    user = bits.UserKeyBit()