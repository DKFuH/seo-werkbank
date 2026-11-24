from app.services.tracking_audit import evaluate_consent_requests, inspect_html_tracking


def test_inspect_html_tracking_detects_tags_and_cmps():
    sample_html = """<!DOCTYPE html>
    <html lang="de">
    <head>
        <title>Test Page</title>
        <!-- GTM Container -->
        <script src="https://www.googletagmanager.com/gtm.js?id=GTM-TEST123"></script>
        <!-- GA4 Config -->
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-ABC123XYZ4');
            gtag('config', 'G-ABC123XYZ4'); /* Duplicate config call */
        </script>
        <!-- Cookiebot CMP -->
        <script src="https://consent.cookiebot.com/uc.js" data-cbid="0000-0000" id="Cookiebot"></script>
    </head>
    <body>
        <h1>Kontakt</h1>
        <a href="tel:+49123456789">Rufen Sie uns an</a>
        <a href="tel:+49987654321" onclick="gtag('event', 'phone_call');">Notfall-Telefon</a>
        <a href="mailto:info@example.com">E-Mail schreiben</a>
        <form id="contact-form" action="/send" method="post">
            <input type="text" name="name" />
            <button type="submit">Absenden</button>
        </form>
    </body>
    </html>
    """
    res = inspect_html_tracking(sample_html, "https://example.com/kontakt")
    assert "error" not in res
    assert "G-ABC123XYZ4" in res["tags"]["google_analytics_4"]
    assert "GTM-TEST123" in res["tags"]["google_tag_manager"]
    assert "Cookiebot" in res["cmps_detected"]

    # Duplicates check
    assert any("G-ABC123XYZ4" in d for d in res["duplicates"])

    # Conversion targets
    targets = res["conversion_targets"]
    assert targets["tel_count"] == 2
    assert targets["tel_untracked_count"] == 1
    assert targets["mailto_count"] == 1
    assert targets["form_count"] == 1


def test_inspect_html_tracking_matomo_and_clarity():
    sample_html = """<!DOCTYPE html>
    <html>
    <head>
        <script>
            var _paq = window._paq = window._paq || [];
            _paq.push(['trackPageView']);
            _paq.push(['setTrackerUrl', 'https://stats.example.org/matomo.php']);
            _paq.push(['setSiteId', '42']);
            (function() {
                var u="//stats.example.org/";
                var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
                g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
            })();
            (function(c,l,a,r,i,t,y){
                c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
                t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
                y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
            })(window, document, "clarity", "script", "clarityid99");
        </script>
    </head>
    <body>
        <p>Hallo</p>
    </body>
    </html>
    """
    res = inspect_html_tracking(sample_html, "https://example.org/")
    assert res["tags"]["matomo"]["active"] is True
    assert "42" in res["tags"]["matomo"]["site_ids"]
    assert "clarityid99" in res["tags"]["clarity"]


def test_evaluate_consent_requests_leakage():
    samples = [
        {
            "choice": "initial",
            "requests": [
                {"host": "example.com", "third_party": False},
                {"host": "www.google-analytics.com", "third_party": True},
            ],
        },
        {
            "choice": "reject",
            "requests": [
                {"host": "example.com", "third_party": False},
            ],
        },
    ]
    eval_res = evaluate_consent_requests(samples)
    assert eval_res["verdict"] == "kritisch_leakage_vor_consent"
    assert eval_res["initial_state_leakage"]["has_leakage"] is True
    assert "www.google-analytics.com" in eval_res["initial_state_leakage"]["tracking_hosts_fired_before_consent"]


def test_api_tracking_diagnostics_endpoints(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Audit Site", "url": fixture_site.url}).json()
    site_id = site["id"]

    # 1. Test tracking overview endpoint
    overview = client.get(f"/api/sites/{site_id}/diagnostics/tracking-overview", headers=auth)
    assert overview.status_code == 200
    assert "conversion_links" in overview.json()

    # 2. Test tracking audit endpoint against fixture_site.url
    audit = client.post(f"/api/sites/{site_id}/diagnostics/tracking-audit", headers=auth, json={
        "url": fixture_site.url + "/",
        "run_browser_consent": False,
    })
    assert audit.status_code == 200
    res = audit.json()
    assert "static_inspection" in res
    assert "tags" in res["static_inspection"]
    assert "conversion_targets" in res["static_inspection"]

