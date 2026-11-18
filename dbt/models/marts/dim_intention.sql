select type
from unnest(
    ['informationnelle', 'transactionnelle', 'navigationnelle', 'commerciale']
) as type
