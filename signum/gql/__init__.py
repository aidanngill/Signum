import os

path = os.path.dirname(os.path.abspath(__file__))
operations = {}

for file_name in os.listdir(path):
    if not os.path.isfile(os.path.join(path, file_name)):
        continue

    with open(os.path.join(path, file_name), "r", encoding="utf-8") as file_object:
        operations[file_name.split(".graphql")[0]] = "\n".join([
            line
            for line
            in file_object.read().strip().splitlines()
            if not line.startswith("#")
        ])

hashes = {
    "ChannelPointsContext": "9988086babc615a918a1e9a722ff41d98847acac822645209ac7379eecb27152",
    "ClaimCommunityPoints": "46aaeebe02c99afdf4fc97c7c0cba964124bf6b0af229395f1f6d1feed05b3d0",
}
