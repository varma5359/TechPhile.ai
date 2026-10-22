"""Optional, cached market research; no search provider is enabled by default."""

import hashlib
import json
from datetime import date
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from .models import MarketResearchCache

VACANCY_STATES = {'verified_open', 'closed', 'expired', 'unverified'}
_providers = {}


def register_research_provider(name, provider):
    """Register an integration explicitly; the app ships with none enabled."""
    _providers[name] = provider


def _cache_key(provider_name, role_family, query):
    material = json.dumps([provider_name, role_family, query.casefold().strip()], separators=(',', ':'))
    return hashlib.sha256(material.encode('utf-8')).hexdigest()


def _validate_results(items, now):
    if not isinstance(items, list):
        raise ValueError('Research providers must return a list of source records.')
    clean = []
    for index, item in enumerate(items[:10], start=1):
        if not isinstance(item, dict):
            continue
        url = str(item.get('url', '')).strip()
        parsed = urlparse(url)
        state = item.get('vacancy_status', 'unverified')
        if parsed.scheme != 'https' or not parsed.netloc or state not in VACANCY_STATES:
            continue
        published = item.get('published_at')
        expires = item.get('expires_at')
        if state == 'verified_open':
            # Only the integration that inspected the official employer page
            # may assert an open role; records must carry dated source evidence.
            if not item.get('official_employer_source') or not published:
                state = 'unverified'
            else:
                try:
                    posted_date = date.fromisoformat(str(published)[:10])
                except ValueError:
                    state = 'unverified'
                else:
                    if posted_date > now.date() or (now.date() - posted_date).days > 180:
                        state = 'unverified'
                    elif expires:
                        try:
                            expires_date = date.fromisoformat(str(expires)[:10])
                        except ValueError:
                            state = 'unverified'
                        else:
                            if expires_date < now.date():
                                state = 'expired'
        clean.append({
            'id': str(item.get('id') or f'MKT-{index}'),
            'title': str(item.get('title', '')).strip()[:255],
            'employer': str(item.get('employer', '')).strip()[:255],
            'url': url,
            'published_at': published,
            'retrieved_at': now.isoformat(),
            'vacancy_status': state,
            'official_employer_source': bool(item.get('official_employer_source')),
            'evidence': str(item.get('evidence', '')).strip()[:1200],
        })
    return clean


def research_job_market(role_family, job_title, company_name=''):
    """Return cached evidence or explicitly report that research was skipped."""
    provider_name = settings.INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER
    provider = _providers.get(provider_name)
    if provider_name == 'none' or provider is None:
        return {'status': 'not_performed', 'provider': None, 'sources': [], 'message': 'Current vacancy research was not performed.'}

    query = ' '.join(part for part in (job_title, company_name) if part).strip()
    now = timezone.now()
    key = _cache_key(provider_name, role_family, query)
    cached = MarketResearchCache.objects.filter(cache_key=key, expires_at__gt=now).first()
    if cached:
        return {'status': 'cached', 'provider': cached.provider, 'sources': cached.results, 'fetched_at': cached.fetched_at.isoformat(), 'cost_usd': str(cached.cost_usd) if cached.cost_usd is not None else None}

    provider_result = provider.search(
        job_title=job_title,
        company_name=company_name,
        role_family=role_family,
        prioritize_official_employer_pages=True,
        recent_days=180,
    )
    if isinstance(provider_result, dict):
        raw = provider_result.get('sources', [])
        cost_usd = provider_result.get('cost_usd')
    else:
        raw = provider_result
        cost_usd = None
    if cost_usd is not None:
        try:
            cost_usd = float(cost_usd)
            if cost_usd < 0:
                cost_usd = None
        except (TypeError, ValueError):
            cost_usd = None
    results = _validate_results(raw, now)
    fetched_at = now
    expires_at = now + timedelta(hours=settings.INTERVIEW_PREP_MARKET_RESEARCH_CACHE_HOURS)
    MarketResearchCache.objects.update_or_create(
        cache_key=key,
        defaults={
            'role_family': role_family,
            'query': query[:255],
            'results': results,
            'provider': provider_name,
            'cost_usd': cost_usd,
            'fetched_at': fetched_at,
            'expires_at': expires_at,
        },
    )
    return {'status': 'completed' if results else 'no_sources', 'provider': provider_name, 'sources': results, 'fetched_at': fetched_at.isoformat(), 'cost_usd': str(cost_usd) if cost_usd is not None else None}
