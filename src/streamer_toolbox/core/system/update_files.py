# The files an update leaves in the settings folder's cache/update, apart from the code that writes them, so
# the starter and the launcher can read them without loading the web client (httpx) of ToolboxUpdate.
READY = "ready.json"  # a downloaded update waiting for the toolbox to stop (UpdateStarter reads it)
RESULT = "result.json"  # what the last swap did (UpdateSwap writes it)
