import asyncio
from vespa.application import Vespa

def get_vespa_connection():
    """
    Get the connection to the vespa server
    :return: The connection to the vespa server
    """
    # update the url and port to the vespa server
    connection = Vespa(url="http://127.0.0.1", port="2222")
    return connection


async def get_asset_data_from_vespa(asset_id: str| None = None, search_string: str| None = None) -> list:
    if not any([asset_id, search_string]):
        return ""

    connection = get_vespa_connection()
    index: str = "your_vespa_schema_index_name" 
    vespa_vector_search_target_hits = 100000
    result: list = []
    if asset_id:
        json_data = connection.get_data(index, asset_id)
        result: list = json_data.json.get("fields").get("full_text", "")
    elif search_string:
        yql: str = f'select full_text from {index} where status contains "published"'
        yql: str = (
                    yql + f' AND (title contains "{search_string}" OR full_text contains "{search_string}" OR '
                    f"({{targetHits:{vespa_vector_search_target_hits}}}"
                    f"nearestNeighbor(paragraph_embeddings, q)))"
                )

        query_body: dict = {
                "input.query(q)": f'embed(mini, "{search_string}")',
                "input.query(query_token_ids)": f'embed(tokenizer, "{search_string}")',
                "ranking.profile": "transformer",
                "ranking.matching.postFilterThreshold": 0.0,
                "ranking.matching.approximateThreshold": 0.05,
                "hits": 1,
            }

        query_body["yql"] = yql
        # select_query = {
        #     'yql': f'select documentid,title, name,paragraph, category from {index} where paragraph contains "{search_string}"',
        #     'hits': 100000
        # }
        response = connection.query(body=query_body).json
        if response and response.get("root", {}).get("children"):
            result: list = [children["fields"].get("full_text") for children in response['root']['children'] if response['root']['children']]
    return result
