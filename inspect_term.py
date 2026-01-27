from google.cloud import dataplex_v1
import inspect

print("Fields in GlossaryTerm:")
# GlossaryTerm is a proto message
print(dataplex_v1.GlossaryTerm.meta.fields.keys())
