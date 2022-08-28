from typing import Callable
from typing import Collection
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Tuple
from typing import Union
from csnake import Variable,CodeWriterLite,Struct,CodeWriter
def assure_str(supposed_str) -> str:
    if not isinstance(supposed_str, str):
        raise TypeError(f"supposed_str ({supposed_str}) must be a str")
    return supposed_str

def _get_variable(variable: Union[Variable, Collection, Mapping]) -> Variable:
    """Get a Variable out of one of the following:

    * a Variable (idempotent)

    * a Collection (tuple/list-like) of 2 strings (name, primitive)

    * a Mapping (dict-like) with keys (name, primitive)
    """
    if isinstance(variable, Variable):
        return variable
    elif isinstance(variable, Mapping):
        var = Variable(**variable)
        return var
    elif isinstance(variable, Collection):
        if len(variable) != 2:
            raise TypeError(
                "variable must be a Collection with len(variable) == 2"
            )
        var = Variable(*variable)
        return var
    else:
        raise TypeError(
            "variable must be one of (Variable, Collection, Mapping)"
        )

class Union(Struct):
    """Class describing C :ccode:`union` construct.

    Args:
        name: name of union
        typedef: whether or not the union is :ccode:`typedef`'d

    Attributes:
        name: name of union
        typedef: whether or not the union is :ccode:`typedef`'d
        variables: :obj:`list` of :ccode:`union`'s variables
    """

    __slots__ = ("name", "variables", "typedef")

    def __init__(self, name: str, typedef: bool = False) -> None:
        self.name = assure_str(name)
        self.variables: List[Variable] = []
        self.typedef = bool(typedef)

    def add_variable(self, variable: Union[Variable, Collection, Mapping]):
        """Add a variable to `union`.

        Variables inside of a :class:`union` are ordered (added sequentially).

        Args:
            variable: variable to add. It can be defined in multiple ways.

                `variable` can be:

                * a :class:`Variable`
                * a :class:`Collection` (:obj:`tuple`/:obj:`list`-like) of 2
                    :obj:`str`\\ s (`name`, `primitive`)
                * a :class:`Mapping` (:obj:`dict`-like) with keys ['name',
                    'primitive']
        """

        proc_var = _get_variable(variable)
        self.variables.append(proc_var)

    def generate_declaration(
        self, indent: Union[int, str] = 4
    ) -> CodeWriterLite:
        """Generate a :class:`CodeWriterLite` instance containing the
        initialization code for this :class:`union`.

        Args:
            indent: indent :obj:`str` or :obj:`int` denoting the number of
                spaces for indentation

        Example:
            >>> from csnake import Variable, union
            >>> strct = union("strname", typedef=False)
            >>> var1 = Variable("var1", "int")
            >>> var2 = Variable("var2", "int", value=range(10))
            >>> strct.add_variable(var1)
            >>> strct.add_variable(var2)
            >>> strct.add_variable(("var3", "int"))
            >>> strct.add_variable({"name": "var4", "primitive": "int"})
            >>> print(strct.generate_declaration())
            union strname
            {
                int var1;
                int var2[10];
                int var3;
                int var4;
            };
        """
        writer = CodeWriterLite(indent=indent)

        if self.typedef:
            writer.add_line("typedef union")
        else:
            writer.add_line(f"union {self.name}")

        writer.open_brace()
        for var in self.variables:
            writer.add_line(var.declaration)
        writer.close_brace()

        if self.typedef:
            writer.add(" " + self.name + ";")
        else:
            writer.add(";")

        return writer

    @property
    def declaration(self):
        """:class:`CodeWriterLite` instance containing the
        declaration code for this :class:`union`.

        See Also:
            :meth:`generate_declaration` for the underlying method.
        """

        return self.generate_declaration()

    def __str__(self):
        """Generate a :obj:`str` instance containing the
        declaration code for this :class:`union`."""
        return str(self.generate_declaration())




