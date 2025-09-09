class Version:
    def __init__(self, *components: int):
        self.__components = tuple(components)

    @property
    def major(self):
        return self.__components[0] if len(self.__components) > 0 else 0

    @property
    def minor(self):
        return self.__components[1] if len(self.__components) > 1 else 0

    @property
    def revision(self):
        return self.__components[2] if len(self.__components) > 2 else 0

    @property
    def build(self):
        return self.__components[3] if len(self.__components) > 3 else 0

    def truncate(self, pos: int):
        return Version(*self.__components[:pos])

    def __str__(self):
        return ".".join(map(str, self.__components))

    __repr__ = __str__

    @staticmethod
    def __compare(v1: "Version", v2: "Version") -> int:
        c1 = v1.__components
        c2 = v2.__components
        # Zero pad
        if len(c1) < len(c2):
            c1 += (0,) * (len(c2) - len(c1))
        elif len(c2) < len(c1):
            c2 += (0,) * (len(c1) - len(c2))
        for c1, c2 in zip(v1.__components, v2.__components):
            if c1 > c2:
                return 1
            elif c1 < c2:
                return -1
        return 0

    def __gt__(self, other: "Version"):
        if isinstance(other, Version):
            return self.__compare(self, other) == 1
        else:
            raise TypeError(f"Expected other to have type {Version}, got {type(other)}")

    def __ge__(self, other: "Version"):
        if isinstance(other, Version):
            return self.__compare(self, other) in [0, 1]
        else:
            raise TypeError(f"Expected other to have type {Version}, got {type(other)}")

    def __lt__(self, other: "Version"):
        if isinstance(other, Version):
            return self.__compare(self, other) == -1
        else:
            raise TypeError(f"Expected other to have type {Version}, got {type(other)}")

    def __le__(self, other: "Version"):
        if isinstance(other, Version):
            return self.__compare(self, other) in [-1, 0]
        else:
            raise TypeError(f"Expected other to have type {Version}, got {type(other)}")

    def __eq__(self, other: "Version"):
        if isinstance(other, Version):
            return self.__compare(self, other) == 0
        else:
            raise TypeError(f"Expected other to have type {Version}, got {type(other)}")

    def __ne__(self, other: "Version"):
        if isinstance(other, Version):
            return self.__compare(self, other) != 0
        else:
            raise TypeError(f"Expected other to have type {Version}, got {type(other)}")

    @property
    def components(self):
        return self.__components

    @classmethod
    def from_str(cls, version_string: str):
        return cls(*map(int, version_string.split(".")))

    @classmethod
    def create(cls, major: int = 0, minor: int = 0, revision: int = 0, build: int = 0):
        return cls(major, minor, revision, build)
