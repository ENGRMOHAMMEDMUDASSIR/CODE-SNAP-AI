# backend/comparator.py
import requests
import os

def compare_repositories(repos_data: list):
    """Compare multiple repositories and return insights"""
    
    if len(repos_data) < 2:
        return {"error": "Need at least 2 repositories to compare"}
    
    comparison = {
        "total_repos": len(repos_data),
        "star_ranking": sorted(repos_data, key=lambda x: x.get('stars', 0), reverse=True),
        "fork_ranking": sorted(repos_data, key=lambda x: x.get('forks', 0), reverse=True),
        "issue_ranking": sorted(repos_data, key=lambda x: x.get('open_issues', 0), reverse=True),
        "language_distribution": {},
        "insights": []
    }
    
    # Language distribution
    for repo in repos_data:
        lang = repo.get('language', 'Unknown')
        comparison["language_distribution"][lang] = comparison["language_distribution"].get(lang, 0) + 1
    
    # Generate insights
    top_star = comparison["star_ranking"][0]
    comparison["insights"].append(f"⭐ {top_star['full_name']} has the most stars ({top_star['stars']})")
    
    top_fork = comparison["fork_ranking"][0]
    comparison["insights"].append(f"🍴 {top_fork['full_name']} has the most forks ({top_fork['forks']})")
    
    # Calculate averages
    avg_stars = sum(r.get('stars', 0) for r in repos_data) / len(repos_data)
    avg_forks = sum(r.get('forks', 0) for r in repos_data) / len(repos_data)
    
    comparison["averages"] = {
        "avg_stars": round(avg_stars, 1),
        "avg_forks": round(avg_forks, 1)
    }
    
    # Add recommendation
    if len(repos_data) >= 2:
        best_quality = max(repos_data, key=lambda x: x.get('stars', 0) / (x.get('open_issues', 1) + 1))
        comparison["insights"].append(f"📊 {best_quality['full_name']} has the best star-to-issue ratio")
    
    return comparison