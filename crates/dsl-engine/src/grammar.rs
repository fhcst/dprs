use pest_derive::Parser;

#[derive(Parser)]
#[grammar = "dsl.pest"]
pub struct DslParser;
