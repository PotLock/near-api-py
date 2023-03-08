from typing import Union


class BinarySerializer:
    def __init__(self, schema: dict):
        self.array = bytearray()
        self.schema = schema

    def serialize_num(self, value: int, n_bytes: int):
        orig_value = value
        if value < 0:
            raise Exception("Can't serialize negative numbers %d" % value)
        for i in range(n_bytes):
            self.array.append(value & 255)
            value //= 256
        if value != 0:
            raise Exception("Value %d has more than %d bytes" % (orig_value, n_bytes))

    def serialize_field(self, value: Union[str, int], field_type: Union[str, list, dict, type]):
        try:
            if type(field_type) == str:
                if field_type[0] == 'u':
                    self.serialize_num(value, int(field_type[1:]) // 8)
                elif field_type == 'string':
                    b = value.encode('utf8')
                    self.serialize_num(len(b), 4)
                    self.array += b
                else:
                    raise Exception(f"invalid str field_type: {field_type}")
            elif type(field_type) == list:
                if len(field_type) != 1:
                    raise Exception("field_type list can only contain 1 element")
                if type(field_type[0]) == int:
                    if type(value) != bytes:
                        raise Exception("type(%s) = %s != bytes" % (value, type(value)))
                    if len(value) != field_type[0]:
                        raise Exception("len(%s) = %s != %s" % (value, len(value), field_type[0]))
                    self.array += bytearray(value)
                else:
                    self.serialize_num(len(value), 4)
                    for el in value:
                        self.serialize_field(el, field_type[0])
            elif type(field_type) == dict:
                if field_type['kind'] != "option":
                    raise Exception(f"invalid dict filed_type kind: {field_type['kind']}")
                if value is None:
                    self.serialize_num(0, 1)
                else:
                    self.serialize_num(1, 1)
                    self.serialize_field(value, field_type['type'])
            elif type(field_type) == type:
                if type(value) != field_type:
                    raise Exception("%s != type(%s)" % (field_type, value))
                self.serialize_struct(value)
            else:
                raise Exception(f"invalid field_type type: {type(field_type)}")
        except Exception:
            print("Failed to serialize %s as %s" % (value, field_type))
            raise

    def serialize_struct(self, obj):
        struct_schema = self.schema[type(obj)]
        if struct_schema['kind'] == "struct":
            for fieldName, fieldType in struct_schema['fields']:
                self.serialize_field(getattr(obj, fieldName), fieldType)
        elif struct_schema['kind'] == "enum":
            name = getattr(obj, struct_schema['field'])
            for idx, (fieldName, fieldType) in enumerate(struct_schema['values']):
                if fieldName == name:
                    self.serialize_num(idx, 1)
                    self.serialize_field(getattr(obj, fieldName), fieldType)
                    break
        else:
            raise Exception(f"invalid struct_scheme: {struct_schema}")

    def serialize(self, obj):
        self.serialize_struct(obj)
        return bytes(self.array)
