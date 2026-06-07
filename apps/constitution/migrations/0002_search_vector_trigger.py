from django.db import migrations


CREATE_SQL = r"""
CREATE OR REPLACE FUNCTION constitution_article_tsv_trigger() RETURNS trigger AS $$
begin
  new.search_vector :=
    to_tsvector('french', coalesce(new.title, '') || ' ' || coalesce(new.content, ''));
  return new;
end
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS constitution_article_tsv_update ON constitution_constitutionarticle;

CREATE TRIGGER constitution_article_tsv_update
BEFORE INSERT OR UPDATE OF title, content
ON constitution_constitutionarticle
FOR EACH ROW EXECUTE FUNCTION constitution_article_tsv_trigger();

UPDATE constitution_constitutionarticle
SET search_vector =
    to_tsvector('french', coalesce(title, '') || ' ' || coalesce(content, ''));
"""

DROP_SQL = r"""
DROP TRIGGER IF EXISTS constitution_article_tsv_update ON constitution_constitutionarticle;
DROP FUNCTION IF EXISTS constitution_article_tsv_trigger();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("constitution", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(CREATE_SQL, DROP_SQL),
    ]
