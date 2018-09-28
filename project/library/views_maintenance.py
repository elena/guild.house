# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.shortcuts import redirect
from django.views import generic

from .forms import GameAddBGGForm
from .models import Copy, Game, CHOICE_LOCATIONS


class GameAddBGGID(generic.FormView):

    template_name = "library/game_bgg_add.html"
    form_class = GameAddBGGForm

    def form_valid(self, form):
        this_game = Game.create_from_bgg_id(form.cleaned_data['BGGID'])
        return redirect("/admin/library/game/{}/change/".format(this_game.pk))

    # Add game, shelf, priority


class MaintenanceRegister(generic.ListView):

    model = Game
    template_name = "library/maintenance/list.html"

    def get_context_object(self, *args, **kwargs):
        context = super(MaintenanceRegister,
                        self).get_context_object(*args, **kwargs)
        context['shelves'] = CHOICE_LOCATIONS
        return context


class MaintainGame(generic.UpdateView):

    model = Game
    fields = ['name',
              'categories',
              'series',
              'featured_image',
              'publisher',
              'boardgamegeek_id',
              'boardgamegeek_rank',
              'boardgamegeek_img',
              'complexity',
              'minimum_players',
              'maximum_players',
              'minimum_playtime',
              'maximum_playtime',
              'year_published',
              'title',
              'heading',
              'featured_content',
              'content',
              'meta_description',
              'has_consumables',
              'priority',
              'is_new',
              'is_free',
              'is_enabled',
              'is_featured',
              'site',
              'slug',
              ]
    template_name = "library/maintenance/game.html"

    def get_object(self):
        return Game.objects.get(id=self.kwargs['pk'])


class MaintainCopy(generic.UpdateView):

    model = Copy
    template_name = "library/maintenance/copy.html"
    fields = [
        'location',
        'is_dead',
        'is_lost',
        'added_at',
        'removed_at',
        'notes'
    ]

    def get_object(self):
        return Copy.objects.get(
            game__pk=self.kwargs['pk'],
            num=self.kwargs['num']
        )


class AddCopy(generic.CreateView):

    model = Copy
    template_name = "library/maintenance/copy.html"
    fields = [
        'game',
        'location',
        'is_dead',
        'is_lost',
        'added_at',
        'removed_at',
        'notes'
    ]
    success_url = '/games/m/'