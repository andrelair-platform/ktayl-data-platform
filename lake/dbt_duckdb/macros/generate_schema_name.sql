{# Use the custom schema name VERBATIM (marts → lake) instead of dbt's default
   target.schema + custom concatenation (which produced `main_lake`). Same override as the warehouse
   dbt project — safe here because this is a single-target, single-owner analytics DB. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
