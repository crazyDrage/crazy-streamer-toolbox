"""A clip question the way a web player's packed code holds it (a parsed GraphQL Document as a JavaScript
object: no quotes around the keys, !1 for false), with code around it. Made up, in the shape Twitch's has."""


def name(value: str) -> str:
    return f'{{kind:"Name",value:"{value}"}}'


def field(value: str, inside: str = "", arguments: str = "") -> str:
    selection = f',selectionSet:{{kind:"SelectionSet",selections:[{inside}]}}' if inside else ""
    return f'{{kind:"Field",name:{name(value)},arguments:[{arguments}],directives:[]{selection}}}'


def player_code(operation: str = "VideoAccessToken_Clip", player_type: str = "clips-viewing") -> str:
    params = (f'{{kind:"Argument",name:{name("params")},value:{{kind:"ObjectValue",fields:['
              f'{{kind:"ObjectField",name:{name("platform")},value:{{kind:"Variable",name:{name("platform")}}}}},'
              f'{{kind:"ObjectField",name:{name("playerType")},value:{{kind:"StringValue",value:"{player_type}",'
              f'block:!1}}}}]}}}}')
    slug = f'{{kind:"Argument",name:{name("slug")},value:{{kind:"Variable",name:{name("slug")}}}}}'
    spread = f'{{kind:"FragmentSpread",name:{name("quality")},directives:[]}}'
    clip = field("clip", ",".join([field("id"), field("playbackAccessToken", field("signature") + "," + field("value"),
                                                        params), field("videoQualities", spread)]), slug)
    variables = ",".join([
        f'{{kind:"VariableDefinition",variable:{{kind:"Variable",name:{name("slug")}}},type:{{kind:"NonNullType",'
        f'type:{{kind:"NamedType",name:{name("ID")}}}}},directives:[]}}',
        f'{{kind:"VariableDefinition",variable:{{kind:"Variable",name:{name("platform")}}},type:{{kind:"NonNullType",'
        f'type:{{kind:"NamedType",name:{name("String")}}}}},directives:[]}}',
        f'{{kind:"VariableDefinition",variable:{{kind:"Variable",name:{name("codecs")}}},type:{{kind:"ListType",'
        f'type:{{kind:"NonNullType",type:{{kind:"NamedType",name:{name("VideoCodec")}}}}}}},defaultValue:'
        f'{{kind:"ListValue",values:[{{kind:"EnumValue",value:"AVC"}}]}},directives:[]}}'])
    document = (f'{{kind:"Document",definitions:[{{kind:"OperationDefinition",operation:"query",name:{name(operation)},'
                f'variableDefinitions:[{variables}],directives:[],selectionSet:{{kind:"SelectionSet",selections:'
                f'[{clip}]}}}},{{kind:"FragmentDefinition",name:{name("quality")},typeCondition:{{kind:"NamedType",'
                f'name:{name("ClipVideoQuality")}}},directives:[],selectionSet:{{kind:"SelectionSet",selections:'
                f'[{field("quality")},{field("sourceURL")}]}}}}]}}')
    return ('(self.webpackChunk=self.webpackChunk||[]).push([[1],{1:e=>{var t={kind:"Document",definitions:[]};'
            f'e.exports=t}},334609:e=>{{var t={document};function i(e,t){{if("FragmentSpread"===e.kind)'
            't.add(e.name.value)}e.exports=t}}]);')


QUESTION = ("query VideoAccessToken_Clip($slug: ID!, $platform: String!, $codecs: [VideoCodec!] = [AVC]) "
            "{ clip(slug: $slug) { id playbackAccessToken(params: {platform: $platform, playerType: \"clips-viewing\"}) "
            "{ signature value } videoQualities { ...quality } } }\n"
            "fragment quality on ClipVideoQuality { quality sourceURL }")
