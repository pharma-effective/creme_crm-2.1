# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.conf import settings
from django.db.models import (CharField, TextField, PositiveSmallIntegerField,
        ForeignKey, ManyToManyField, CASCADE)
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeEntity, CremeModel

from .market_segment import MarketSegment


__all__ = ('AbstractStrategy', 'Strategy',
           'MarketSegmentDescription', 'MarketSegmentCategory',
           'CommercialAsset', 'CommercialAssetScore',
           'MarketSegmentCharm', 'MarketSegmentCharmScore',
          )

_CATEGORY_MAP = {
         0: 4,  # Weak charms   & weak assets
         1: 2,  # Strong charms & weak assets
        10: 3,  # Weak charms   & strong assets
        11: 1,  # Strong charms & strong assets
    }


class AbstractStrategy(CremeEntity):
    name            = CharField(_('Name'), max_length=100)
    evaluated_orgas = ManyToManyField(settings.PERSONS_ORGANISATION_MODEL,
                                      verbose_name=_('Evaluated organisation(s)'),
                                      editable=False,
                                     )

    creation_label = _('Create a strategy')
    save_label     = _('Save the strategy')

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'commercial'
        verbose_name = _('Commercial strategy')
        verbose_name_plural = _('Commercial strategies')
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._clear_caches()

    def __str__(self):
        return self.name

    def _clear_caches(self):
        self._segments_list = None

        self._assets_list = None
        self._assets_scores_map = {}  # Dict of dict of dict for hierarchy: organisation/segment_description/asset

        self._charms_list = None
        self._charms_scores_map = {}  # Dict of dict of dict for hierarchy: organisation/segment_description/charm

        self._segments_categories = {}

    def get_absolute_url(self):
        return reverse('commercial__view_strategy', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('commercial__create_strategy')

    def get_edit_absolute_url(self):
        return reverse('commercial__edit_strategy', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('commercial__list_strategies')

    def _get_assets_scores_objects(self, orga):
        scores = self._assets_scores_map.get(orga.id)

        if scores is None:
            assets = self.get_assets_list()
            segment_info = self.get_segment_descriptions_list()

            # Build a 'matrix' with default score(=1) everywhere
            scores = {segment_desc.id: {asset.id: CommercialAssetScore(score=1, organisation=orga,
                                                                       asset=asset,
                                                                       segment_desc=segment_desc,
                                                                      )
                                            for asset in assets
                                       }
                        for segment_desc in segment_info
                     }

            # Set the right scores in the matrix
            for score in CommercialAssetScore.objects.filter(organisation=orga,
                                                             asset__in=assets,
                                                             segment_desc__in=segment_info,
                                                            ):
                scores[score.segment_desc_id][score.asset_id] = score

            self._assets_scores_map[orga.id] = scores

        return scores

    # TODO: factorise with _get_assets_scores_objects() ???
    def _get_charms_scores_objects(self, orga):
        scores = self._charms_scores_map.get(orga.id)

        if scores is None:
            charms = self.get_charms_list()
            segment_info = self.get_segment_descriptions_list()

            # Build a 'matrix' with default score(=1) everywhere
            scores = {segment_desc.id: {charm.id: MarketSegmentCharmScore(score=1, organisation=orga,
                                                                          charm=charm, 
                                                                          segment_desc=segment_desc,
                                                                         )
                                            for charm in charms
                                       }
                          for segment_desc in segment_info
                     }

            # Set the right scores in the matrix
            for score in MarketSegmentCharmScore.objects.filter(organisation=orga,
                                                                charm__in=charms,
                                                                segment_desc__in=segment_info,
                                                               ):
                scores[score.segment_desc_id][score.charm_id] = score

            self._charms_scores_map[orga.id] = scores

        return scores

    def _get_asset_score_object(self, orga, asset_id, segment_desc_id):
        return self._get_assets_scores_objects(orga)[segment_desc_id][asset_id]

    def get_asset_score(self, orga, asset, segment):
        return self._get_asset_score_object(orga, asset.id, segment.id).score

    def get_assets_list(self):
        if self._assets_list is None:
            self._assets_list = list(self.assets.all())

        return self._assets_list

    def _get_charm_score_object(self, orga, charm_id, segment_desc_id):
        return self._get_charms_scores_objects(orga)[segment_desc_id][charm_id]

    def get_charm_score(self, orga, charm, segment):
        return self._get_charm_score_object(orga, charm.id, segment.id).score

    def get_charms_list(self):
        if self._charms_list is None:
            self._charms_list = list(self.charms.all())

        return self._charms_list

    def _get_totals(self, orga_scores):
        """@return a list of tuple (total_for_segment, total_category)
        with 1 <= total_category <= 3  (1 is weak, 3 strong)
        """
        if not orga_scores:
            return []

        scores = [sum(score_obj.score for score_obj in orga_scores[segment_desc.id].values())
                    for segment_desc in self.get_segment_descriptions_list()
                 ]
        max_score = max(scores)
        min_score = min(scores)

        def _compute_category(score):
            if score == max_score: return 3
            if score == min_score: return 1

            return 2

        return [(score, _compute_category(score)) for score in scores]

    def get_assets_totals(self, orga):
        return self._get_totals(self._get_assets_scores_objects(orga))

    def get_charms_totals(self, orga):
        return self._get_totals(self._get_charms_scores_objects(orga))

    def get_segment_category(self, orga, segment):
        sid = segment.id

        for category, segments in self._get_segments_categories(orga).items():
            for other_segment in segments:
                if other_segment.id == sid:
                    return category

        raise KeyError('Strategy.get_segment_category() for segment: {}'.format(segment))

    def _get_segments_categories(self, orga):
        """@return A dictionary with key= Category (int, between 1 & 4) and
                   value=list of MarketSegmentDescription.
        """
        categories = self._segments_categories.get(orga)

        if categories is None:
            categories = {i: [] for i in range(1, 5)}
            segment_info = self.get_segment_descriptions_list()

            if segment_info:
                assets_totals = [t[0] for t in self.get_assets_totals(orga)]
                charms_totals = [t[0] for t in self.get_charms_totals(orga)]

                asset_threshold = (max(assets_totals) + min(assets_totals)) / 2.0
                charm_threshold = (max(charms_totals) + min(charms_totals)) / 2.0

                stored_categories = dict(MarketSegmentCategory.objects
                                                              .filter(segment_desc__in=segment_info,
                                                                      organisation=orga,
                                                                     )
                                                              .values_list('segment_desc_id', 'category')
                                        )

                def _get_category(segment, asset_score, charm_score):
                    cat = stored_categories.get(segment.id)

                    if cat is not None:
                        return cat

                    cat_key = 0
                    if charm_score > charm_threshold: cat_key += 1
                    if asset_score > asset_threshold: cat_key += 10

                    return _CATEGORY_MAP[cat_key]

                for segment, asset_total, charm_total in zip(segment_info, assets_totals, charms_totals):
                    categories[_get_category(segment, asset_total, charm_total)].append(segment)

            self._segments_categories[orga] = categories

        return categories

    def get_segments_for_category(self, orga, category):
        return self._get_segments_categories(orga)[category]

    def get_segment_descriptions_list(self):
        if self._segments_list is None:
            self._segments_list = list(self.segment_info.select_related('segment'))

        return self._segments_list

    def _set_score(self, model_id, segment_desc_id, orga_id, score, get_object):
        if not 1 <= score <= 4:
            raise ValueError('Problem with "score" arg: not 1 <= {} <= 4'.format(score))

        orga = self.evaluated_orgas.get(pk=orga_id)  # Raise exception if invalid orga

        score_object = get_object(orga, model_id, segment_desc_id)

        if score_object.score != score:
            score_object.score = score
            score_object.save()

    def set_asset_score(self, asset_id, segment_desc_id, orga_id, score):
        self._set_score(asset_id, segment_desc_id, orga_id, score, self._get_asset_score_object)

    def set_charm_score(self, charm_id, segment_desc_id, orga_id, score):
        self._set_score(charm_id, segment_desc_id, orga_id, score, self._get_charm_score_object)

    def set_segment_category(self, segment_desc_id, orga_id, category):
        if not 1 <= category <= 4:
            raise ValueError('Problem with "category" arg: not 1 <= {} <= 4'.format(category))

        orga    = self.evaluated_orgas.get(pk=orga_id)  # Raise exception if invalid orga
        seg_desc = self.segment_info.get(pk=segment_desc_id)  # Raise exception if invalid segment

        cat_obj = MarketSegmentCategory.objects.filter(segment_desc=seg_desc, organisation=orga).first()

        if cat_obj:
            if cat_obj.category == category:
                return

            cat_obj.category = category
            cat_obj.save()
        else:
            MarketSegmentCategory.objects.create(strategy=self, segment_desc=seg_desc,
                                                 organisation=orga, category=category,
                                                )

        self._segments_categories.pop(orga.id, None)  # Clean cache


class Strategy(AbstractStrategy):
    class Meta(AbstractStrategy.Meta):
        swappable = 'COMMERCIAL_STRATEGY_MODEL'


class MarketSegmentDescription(CremeModel):
    strategy  = ForeignKey(settings.COMMERCIAL_STRATEGY_MODEL, related_name='segment_info',
                           editable=False, on_delete=CASCADE,
                          )
    segment   = ForeignKey(MarketSegment, on_delete=CASCADE)  # TODO: PROTECT
    product   = TextField(_('Product'), blank=True)
    place     = TextField(pgettext_lazy('commercial-4p', 'Place'), blank=True)
    price     = TextField(_('Price'), blank=True)
    promotion = TextField(_('Promotion'), blank=True)

    creation_label = _('Create a market segment')
    save_label     = _('Save the market segment')

    class Meta:
        app_label = 'commercial'
        verbose_name = _('Market segment description')
        verbose_name_plural = _('Market segment descriptions')

    def __repr__(self):
        return 'MarketSegmentDescription(strategy_id={}, segment_id={}, ' \
               'product={}, place={}, price={}, promotion={})'.format(
                self.strategy_id, self.segment_id, self.product,
                self.place, self.price, self.promotion,
            )

    def __str__(self):
        return self.segment.name

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

        self.strategy._clear_caches()  # NB: not really useful...

    def get_related_entity(self):  # For generic views
        return self.strategy


class CommercialAsset(CremeModel):
    name     = CharField(_('Name'), max_length=100)
    strategy = ForeignKey(settings.COMMERCIAL_STRATEGY_MODEL, related_name='assets', editable=False, on_delete=CASCADE)

    creation_label = _('Create a commercial asset')
    save_label     = _('Save the commercial asset')

    class Meta:
        app_label = 'commercial'
        verbose_name = _('Commercial asset')
        verbose_name_plural = _('Commercial assets')

    def __str__(self):
        return self.name

    def get_edit_absolute_url(self):
        return reverse('commercial__edit_asset', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.strategy


class CommercialAssetScore(CremeModel):
    score        = PositiveSmallIntegerField()
    segment_desc = ForeignKey(MarketSegmentDescription, on_delete=CASCADE)
    asset        = ForeignKey(CommercialAsset, on_delete=CASCADE)
    organisation = ForeignKey(settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)

    class Meta:
        app_label = 'commercial'

    def __str__(self):  # Debugging
        return '<AssetScore: orga={} score={} segment={} asset={}>'.format(
                    self.organisation, self.score, self.segment_desc, self.asset)


class MarketSegmentCharm(CremeModel):
    name     = CharField(_('Name'), max_length=100)
    strategy = ForeignKey(settings.COMMERCIAL_STRATEGY_MODEL, related_name='charms',
                          editable=False, on_delete=CASCADE,
                         )

    creation_label = _('Create a segment charm')
    save_label     = _('Save the segment charm')

    class Meta:
        app_label = 'commercial'
        verbose_name = _('Segment charm')
        verbose_name_plural = _('Segment charms')

    def __str__(self):
        return self.name

    def get_edit_absolute_url(self):
        return reverse('commercial__edit_charm', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.strategy


class MarketSegmentCharmScore(CremeModel):
    score        = PositiveSmallIntegerField()
    segment_desc = ForeignKey(MarketSegmentDescription, on_delete=CASCADE)
    charm        = ForeignKey(MarketSegmentCharm, on_delete=CASCADE)
    organisation = ForeignKey(settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)

    class Meta:
        app_label = 'commercial'

    def __str__(self):  # Debugging
        return '<CharmScore: orga={} score={} segment={} charm={}>'.format(
                    self.organisation, self.score, self.segment_desc, self.charm)


class MarketSegmentCategory(CremeModel):
    category     = PositiveSmallIntegerField()
    strategy     = ForeignKey(Strategy, on_delete=CASCADE)
    segment_desc = ForeignKey(MarketSegmentDescription, on_delete=CASCADE)
    organisation = ForeignKey(settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)

    class Meta:
        app_label = 'commercial'

    def __str__(self):  # Debugging
        return '<MarketSegmentCategory: orga={} cat={} segment={}>'.format(
                    self.organisation, self.category, self.segment_desc)
