def panier_context(request):
    panier = request.session.get('panier', {})
    panier_count = sum(item['quantite'] for item in panier.values())
    return {'panier_count': panier_count}