from django.db import migrations


def restore_expected_output(apps, schema_editor):
    Problem = apps.get_model('coding', 'Problem')
    connection = schema_editor.connection
    table_name = Problem._meta.db_table

    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table_name)

    expected_output_column = next(
        (column for column in columns if column.name == 'expected_output'),
        None,
    )
    if expected_output_column is not None and not expected_output_column.null_ok:
        return

    required_field = Problem._meta.get_field('expected_output')
    nullable_field = required_field.clone()
    nullable_field.set_attributes_from_name('expected_output')
    nullable_field.null = True
    nullable_field.blank = True
    nullable_field.model = Problem

    if expected_output_column is None:
        schema_editor.add_field(Problem, nullable_field)

    quoted_table = connection.ops.quote_name(table_name)
    quoted_expected_output = connection.ops.quote_name('expected_output')
    quoted_sample_output = connection.ops.quote_name('sample_output')
    with connection.cursor() as cursor:
        cursor.execute(
            f'UPDATE {quoted_table} '
            f'SET {quoted_expected_output} = {quoted_sample_output} '
            f'WHERE {quoted_expected_output} IS NULL'
        )

    schema_editor.alter_field(
        Problem,
        nullable_field,
        required_field,
        strict=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('coding', '0007_problem_c_solution_problem_cpp_solution_and_more'),
    ]

    atomic = False

    operations = [
        migrations.RunPython(restore_expected_output, migrations.RunPython.noop),
    ]
