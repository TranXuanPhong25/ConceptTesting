"""Three-valued membership receipts shared by scenario measurements."""

def membership_row(identifier, outcomes, source_indices, *, checkable=True):
    hits = [index for index, (value, _) in enumerate(outcomes) if value is True]
    unknown = [index for index, (value, _) in enumerate(outcomes) if value is None]
    return {'id':identifier,
            'status':'hit' if hits else 'unknown' if unknown or not checkable else 'miss',
            'input_indices':hits, 'source_input_indices':[source_indices[index] for index in hits],
            'unknown_input_indices':unknown,
            'input_statuses':['unknown' if value is None else 'hit' if value else 'miss'
                              for value, _ in outcomes],
            'errors':[{'input_index':index,'reason':error} for index, (_, error) in enumerate(outcomes) if error]}


def membership_summary(rows):
    return {'total':len(rows), **{status:sum(row['status'] == status for row in rows)
                                 for status in ('hit','miss','unknown')}}
