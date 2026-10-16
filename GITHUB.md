# Back up your brain to your own GitHub

This puts your brain in a private repository (a folder on GitHub with its full history) that you own.
Nobody else can see it unless you invite them. BrainOS never makes an account or signs in for you, and
nothing goes to any server of ours. About 15 minutes the first time.

Run the commands from the top of your BrainOS download, in Terminal, or ask an AI tool that can run
commands on your computer to run them for you. Replace `~/my-brain` with your brain folder and
`your-name` with your GitHub username.

## 1. Make a GitHub account

Go to https://github.com/signup and follow the steps. The free plan is enough: it includes unlimited
private repositories.

How you know it worked: you can sign in at https://github.com.

## 2. Make an empty, private repository

1. In the top-right corner of any GitHub page, click **+**, then **New repository**.
2. Name it `my-brain`.
3. Choose **Private**.
4. Leave everything else unticked: no README, no .gitignore, no licence. It must start empty.
5. Click **Create repository**.
6. Copy the address that ends in `.git`, for example `https://github.com/your-name/my-brain.git`.

How you know it worked: the new page says **Private** next to the name and shows setup instructions
instead of files.

## 3. See what will happen (nothing runs yet)

`python3 publish_github.py ~/my-brain https://github.com/your-name/my-brain.git`

It lists each command it would run, with one line above each saying what it does. Nothing is changed.

How you know it worked: the last line says to run it again with `--apply`.

## 4. Make a token, so git can sign in as you

GitHub no longer accepts your password from git. You use a token instead: a long password that only
works for the one repository you choose.

1. On GitHub, click your picture (top right), then **Settings**.
2. In the left-hand menu: **Developer settings**, then **Personal access tokens**, then
   **Fine-grained tokens**, then **Generate new token**.
3. Name it `my-brain backup` and pick an expiry date.
4. Under **Repository access**, choose **Only select repositories**, then pick `my-brain`.
5. Under **Permissions**, set **Contents** to **Read and write**.
6. Click **Generate token** and copy it straight away. Keep it in your password manager. Never paste
   it into an AI chat.

How you know it worked: GitHub shows the new token once, on screen.

## 5. Back it up

`python3 publish_github.py ~/my-brain https://github.com/your-name/my-brain.git --apply`

If git asks for a username, type your GitHub username. When it asks for a password, paste the token.
Nothing appears on screen while you paste; that is normal. Press Enter.

How you know it worked: it says `Done. Your brain is backed up to ...`, and the repository's page on
GitHub now shows your brain's files and folders (`CLAUDE.md`, `memory`, `skills` and the rest).

## 6. Next time

Run the step 5 command again. Only what changed is saved and sent. If your computer did not remember
the token, paste it again.

If you would rather click than type, install GitHub Desktop (https://desktop.github.com). After step 5
has worked once, choose **File**, then **Add Local Repository**, pick your brain folder, and use
**Commit** and **Push** there from then on.

## If something goes wrong

The command explains the three usual problems in plain words:

- **The repository already has files in it** (a README was ticked in step 2): make a new, empty one
  and use its address.
- **GitHub did not accept the sign-in**: the password must be the token from step 4, not your GitHub
  password, and the token must be for this repository with Contents set to Read and write.
- **No repository at that address**: copy the address again from the repository's page.

## Your export files stay on your computer

The raw export files in your brain's `exports` folder are never backed up. The brain's `.gitignore` file
tells git to leave them out (only the folder's short README goes up). What you imported from them, in
`memory/`, is backed up.

## Keep it private

Your brain holds other people's messages and details as well as yours: every WhatsApp chat you
imported, for a start. Keep the repository private, and only invite someone you would happily show
those chats to.

## Where these steps come from

Checked against GitHub's own help pages on 1 October 2026. If GitHub's screens have changed, its pages win:

- Making a repository: https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository
- Free plan and private repositories: https://docs.github.com/en/get-started/learning-about-github/githubs-plans
- Tokens instead of passwords: https://docs.github.com/en/get-started/git-basics/about-remote-repositories
- Making a fine-grained token: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- GitHub Desktop, adding a folder: https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-a-repository-from-your-local-computer-to-github-desktop
