# Read-only MCP server (optional)

An **optional, local-only stdio** Model Context Protocol server for assistants that
need SEO-Werkbank information. It uses the existing authenticated REST API, not a
parallel direct database connection. Every call runs under the permissions of
the supplied user token.

## Installation and launch

```bash
cd backend
pip install -e ".[mcp]"
# Sign in to SEO-Werkbank and obtain YOUR account's existing access token.
# Do not use the global SEO_SECRET_KEY.
# Set both environment variables in your MCP client's local secret configuration:
SEO_MCP_API_URL=http://127.0.0.1:8000
SEO_MCP_API_TOKEN=<short-lived user access token>
python -m app.mcp_server
```

Configure the desktop MCP client to launch the command above from `backend`
and pass credentials **through its environment/secret manager**, never via
command-line arguments, JSON committed to Git, or a public endpoint.

The REST API must be running locally. Only `http://localhost:<port>`,
`http://127.0.0.1:<port>` and `http://[::1]:<port>` are accepted.
There is no remotely accessible MCP HTTP endpoint, no automatic token exchange,
no browser login or refresh flow. Access tokens expire as normal and must be
replaced by the user.

## Tools

- `list_owned_sites`: first 100 owned sites
- `get_site_overview`: overview and latest crawl of a site
- `get_crawl_issues`: grouped crawl problems
- `get_crawl_pages`: paginated metadata only, up to 100 pages/call
- `get_gsc_insights`: owned GSC statistics for 7–180 days
- `get_backlinks`: paginated imported/verified links
- `get_keywords`: at most 100 keyword records

No write tools, crawls, exports, arbitrary URLs, passwords, admin settings,
or secret retrieval. Redirects are forbidden, payloads limited to 512 KiB.
A regular user token is required, and tenant isolation remains enforced by
the existing API.

**Limits:** MCP tool responses may include untrusted website text. The agent
must not treat scraped text as instructions. This is an intentionally small
first release, not remote multi-user MCP authentication. Do not expose stdio
via a public relay. Extra endpoints should be security-reviewed individually.
