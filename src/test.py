from vectordb import get_client, get_collection, query
c = get_client("./data/vectors")
col = get_collection(c)
res = query(col, "Scope 1 emissions", n=2)
print(res["metadatas"][0][0]["file_name"], res["metadatas"][0][0]["page"])
print(res["documents"][0][0][:300])