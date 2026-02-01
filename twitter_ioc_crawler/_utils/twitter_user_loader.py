def load_usernames(file_path):
    usernames = []

    if not file_path.exists():
        return usernames

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if not u:
                continue
            if u.startswith("@"):
                u = u[1:]
            usernames.append(u)

    return usernames
