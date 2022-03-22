from collections import OrderedDict

from rest_framework import pagination
from rest_framework.response import Response


class CustomPageNumberPagination(pagination.PageNumberPagination):

    page_size = 100
    page_size_query_param = 'size'
    max_page_size = 50
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('page', self.page.number),
            ('size', self.page_size),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('items', data),
        ]))